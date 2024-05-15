import asyncio
import json
from shlex import quote
from yaml import safe_load
from logging import getLogger

from database import ChallengeState
from port import Port

log = getLogger(__name__)

starting_challenges = set()

class Challenge:
    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self._config = config

        self.ports = list()
        for port in config["ports"]:
            self.ports.append(Port(name, port))

        r = "Make sure you use resource limits on each service to prevent resource exhaustion!"
        if "deploy" not in config:
            log.warning(f"No deploy label for {name}. {r}")
        else:
            if "resources" not in config["deploy"]:
                log.warning(f"No resource label in deploy section of {name}. {r}")
            else:
                if "limits" not in config["deploy"]["resources"]:
                    log.warning(f"No limits label in resources of {name}. {r}")

    async def retrieve_state(self, executor, user_id: str):
        async def retrieve(server):
            if self.name in starting_challenges:
                return

            cmd = f"docker compose -p {quote(user_id)} --project-directory {server.path} ps --format json"
            result = await executor.run(server, cmd)
            if result is None:
                return []
            services = [json.loads(service) for service in result.splitlines()]
            return [service for service in services if service["Service"] == self.name]

        result = await asyncio.gather(
            *[retrieve(server) for server in executor.config.servers]
        )

        idx = None;
        for i in range(len(executor.config.servers)):
            if len(result[i]) > 0:
                idx = i
                break

        db_entry = ChallengeState(executor.config.database, self.name, user_id)
        if idx is None:
            await db_entry.delete()
            return

        entry = result[idx][0]
        await db_entry.delete_and_insert(entry["State"])

        server = executor.config.servers[idx]

        ports = entry["Publishers"]
        ports = [f"{server.ip}:{port["PublishedPort"]}" for port in ports]
        if len(ports) > 0:
            ports = ports[0]
        await db_entry.set(entry["State"], str(ports))

    async def start(self, executor, user_id: str):
        starting_challenges.add(self.name)

        db = executor.config.database
        state = ChallengeState(db, self.name, user_id)

        s = await state.get()
        if s is not None:
            if s == "failed":
                await state.set("scheduled")
            else:
                starting_challenges.remove(self.name)
                return
        else:
            await state.create_challenge()

        await state.set("allocating")
        target_server = await executor.get_available_server()
        if target_server is None:
            await state.set("failed", "no server available")
            starting_challenges.remove(self.name)
            return

        await state.set("building")
        base_cmd = f"docker compose -p {quote(user_id)} --project-directory {target_server.path}"
        cmd = f"{base_cmd} build --with-dependencies {self.name}" 
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "building images failed")
            starting_challenges.remove(self.name)
            return

        await state.set("downing")
        cmd = f"{base_cmd} down {self.name}" 
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "failed shutting down service")
            starting_challenges.remove(self.name)
            return

        await state.set("starting")
        cmd = f"{base_cmd} up -d {self.name}" 
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "failed starting service")
            starting_challenges.remove(self.name)
            return

        await state.set("get_ports")
        ports = []
        for port in self.ports:
            cmd = f"{base_cmd} port {self.name} {port.port}" 
            result = await executor.run(target_server, cmd)
            if result is None:
                await state.set("failed", "failed to get ports")
                starting_challenges.remove(self.name)
                return
            ports.append(result.split(":")[-1])

        ports = [f"{target_server.ip}:{port}" for port in ports]
        await state.set("running", str(ports))
        starting_challenges.remove(self.name)

    async def stop(self, executor, user_id: str):
        pass

    async def status(self, executor, user_id: str):
        pass


def parse_compose(path: str) -> dict[str, Challenge]:
    with open(path) as f:
        data = safe_load(f)
        services = data["services"]

        challenges = dict()
        for name in services:
            config = services[name]

            # Only challenges with exposed ports are treated as challenges
            if "ports" in config:
                challenge = Challenge(name, services[name])
                challenges[name] = challenge

        return challenges
