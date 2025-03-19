import asyncio
import json
import os
import sys

from shlex import quote
from yaml import safe_load
from logging import getLogger

from webapp.database import ChallengeState
from webapp.port import Port

log = getLogger(__name__)


class Challenge:
    def __init__(self, name: str) -> None:
        self.name = name

        class WorkingSet:
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

        self.working_set = WorkingSet()

    async def retrieve_state(self, executor, user_id: str):
        db_entry = ChallengeState(executor.config.database, self.name, user_id)
        if await db_entry.get() is None:
            await db_entry.create_challenge()

        async def retrieve(server):
            cmd = f"docker compose -p {quote(user_id)} --project-directory {server.path} ps --format json"
            result = await executor.run(server, cmd, timeout=1)
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

        if idx is None:
            await db_entry.set("stopped", "challenge not found on a server")
            return

        await db_entry.set_server(idx)
        entry = result[idx][0]
        server = executor.config.servers[idx]

        ports = entry["Publishers"]
        ports = [f"{server.ip}:{port["PublishedPort"]}" for port in ports]
        if len(ports) > 0:
            ports = ports[0]
        await db_entry.set(entry["State"], str(ports))

    async def start(self, executor, user_id: str):
        db = executor.config.database
        state = ChallengeState(db, self.name, user_id)

        s = await state.get()
        if s is not None:
            if s == "failed":
                # Reschedule starting the challenge if it failed before
                await state.set("scheduled")
            elif s == "running":
                # The challenge is already running, so stop trying to start it
                await self.working_set.remove(user_id)
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
            await self.working_set.remove(user_id)
            return

        base_cmd = f"docker compose -p {quote(user_id)} --project-directory {target_server.path}"
        cmd = f"{base_cmd} build --with-dependencies {self.name}"
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "building images failed")
            await self.working_set.remove(user_id)
            return

        cmd = f"{base_cmd} down {self.name}"
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "failed shutting down service")
            await self.working_set.remove(user_id)
            return

        cmd = f"{base_cmd} up -d {self.name}"
        result = await executor.run(target_server, cmd)
        if result is None:
            await state.set("failed", "failed starting service")
            await self.working_set.remove(user_id)
            return

        ports = []
        for port in self.ports:
            cmd = f"{base_cmd} port {self.name} {port.port}"
            result = await executor.run(target_server, cmd)
            if result is None:
                await state.set("failed", "failed to get ports")
                await self.working_set.remove(user_id)
                return
            ports.append(result.split(":")[-1])

        ports = [f"{target_server.ip}:{port}" for port in ports]
        await state.set("running", str(ports))
        await self.working_set.remove(user_id)

    async def stop(self, executor, user_id: str):
        db = ChallengeState(executor.config.database, self.name, user_id)
        server = await db.get_server()
        if server is None:
            await self.working_set.remove(user_id)
            return

        target_server = executor.config.servers[server]
        base_cmd = f"docker compose -p {quote(user_id)} --project-directory {target_server.path}"
        cmd = f"{base_cmd} down {self.name}"
        await executor.run(target_server, cmd)
        await db.delete();
        await self.working_set.remove(user_id)


def parse_challenges(path: str) -> dict[str, Challenge]:
    
    sys.path.append(path)
    print(f"items in the path include: {os.listdir(path)}")
    import checker

    set = checker.ChallengeSet(path)

    parsed_challenges = {}
    for challenge_id, challenge in set.challenges.items():
        parsed_challenges[challenge.name] = Challenge(challenge.name)

    return parsed_challenges
    # with open(path) as f:
    #     data = safe_load(f)
    #     services = data["services"]

    #     challenges = dict()
    #     for name in services:
    #         config = services[name]

    #         # Only challenges with exposed ports are treated as challenges
    #         if "ports" in config:
    #             challenge = Challenge(name, services[name])
    #             challenges[name] = challenge

    #     return challenges
