import asyncio
import json
from shlex import quote
from yaml import safe_load
from logging import getLogger

from database import ChallengeState
from port import Port

log = getLogger(__name__)

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

        class StartingInstances:
            def __init__(self) -> None:
                self.challenges = set()
                self.lock = asyncio.Lock()

            async def add(self, user_id):
                async with self.lock:
                    self.challenges.add(user_id)

            async def contains_or_insert(self, user_id):
                async with self.lock:
                    if user_id in self.challenges:
                        return False
                    else:
                        self.challenges.add(user_id)
                        return True

            async def remove(self, user_id):
                async with self.lock:
                    self.challenges.remove(user_id)


        self.starting_challenges = StartingInstances()

    async def retrieve_state(self, executor, user_id: str):
        async def retrieve(server):
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
            await db_entry.set("stopped", "challenge not found on a server")
            return

        entry = result[idx][0]
        server = executor.config.servers[idx]

        ports = entry["Publishers"]
        ports = [f"{server.ip}:{port["PublishedPort"]}" for port in ports]
        if len(ports) > 0:
            ports = ports[0]
        await db_entry.set(entry["State"], str(ports))

    async def start(self, executor, user_id: str):
        # If we're already starting this challenge, don't try to start it again
        if not await self.starting_challenges.contains_or_insert(self.name):
            return

        db = executor.config.database
        state = ChallengeState(db, self.name, user_id)

        s = await state.get()
        if s is not None:
            if s == "failed":
                # Reschedule starting the challenge if it failed before
                await state.set("scheduled")
            elif s == "running":
                # The challenge is already running, so stop trying to start it
                await self.starting_challenges.remove(self.name)
                return
            else:
                # The challenge is in another state, so it is marked as starting
                # but it is not in the starting_challenges set. Let's retry
                # starting
                pass
        else:
            await state.create_challenge()

        await state.set("starting")
        target_server = await executor.get_available_server()
        if target_server is None:
            await state.set("failed", "no server available")
            await self.starting_challenges.remove(self.name)
            return

        base_cmd = f"docker compose -p {quote(user_id)} --project-directory {target_server.path}"
        cmd = f"{base_cmd} build --with-dependencies {self.name}" 
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "building images failed")
            await self.starting_challenges.remove(self.name)
            return

        cmd = f"{base_cmd} down {self.name}" 
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "failed shutting down service")
            await self.starting_challenges.remove(self.name)
            return

        cmd = f"{base_cmd} up -d {self.name}" 
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "failed starting service")
            await self.starting_challenges.remove(self.name)
            return

        ports = []
        for port in self.ports:
            cmd = f"{base_cmd} port {self.name} {port.port}" 
            result = await executor.run(target_server, cmd)
            if result is None:
                await state.set("failed", "failed to get ports")
                await self.starting_challenges.remove(self.name)
                return
            ports.append(result.split(":")[-1])

        ports = [f"{target_server.ip}:{port}" for port in ports]
        await state.set("running", str(ports))
        await self.starting_challenges.remove(self.name)

    async def stop(self, executor, user_id: str):
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
