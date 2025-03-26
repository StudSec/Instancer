import asyncio
import json
import os
import sys
import pathlib

from shlex import quote
from yaml import safe_load
from logging import getLogger

from webapp.database import ChallengeState
from webapp.port import Port

log = getLogger(__name__)


class Challenge:
    def __init__(self, name: str, path) -> None:
        self.name = name
        self.path = path

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

        log.info("checking state of challenge!")
        db_entry = ChallengeState(executor.config.database, self.name, user_id)
        if await db_entry.get() is None:
            await db_entry.create_challenge()

        async def retrieve(server):

            # TODO
            port = "6546"
            hostname = "127.0.0.1"

            probe_script_path = pathlib.Path(server.path) / self.path / "Source/probe-status.sh"
            cmd = f"{probe_script_path} --hostname {hostname} --port {port}"
            log.info(f"  + running command: {cmd}")
            result = await executor.run(server, cmd, timeout=1)
            
            # perhaps a better way to do this than checking the string?
            return result
           
        results = await asyncio.gather(
            *[retrieve(server) for server in executor.config.servers]
        )

        log.info(f"  + results are {results}")

        idx = None
        
        for i in range(len(executor.config.servers)):
            if (results[i] is not None and len(results[i]) > 0):
                idx = i
                break

        if idx is None:
            log.info(f"  + results are bogus! challenge not found!")
            await db_entry.set("stopped", "challenge not found on a server")
            return
        elif (results[idx].startswith("[UP]")):
            log.info(f"  + challenge OK")
            await db_entry.set("started")
        elif (results[idx].startswith("[DOWN]")):
            log.info(f"  + challenge is down!")
            await db_entry.set("stopped")
        else:
            log.warning(f"  + probe results parsing went wrong! results: {results}")
            await db_entry.set("failed", results[idx])

    async def start(self, executor, user_id: str):
        log.info("starting challenge!")
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

        log.info("  + setting state")
        await state.set("starting")
        target_server = await executor.get_available_server()

        log.info(f"  + chose server: {target_server}")
        if target_server is None:
            # this is never reached on fail, Why?
            await state.set("failed", "no server available")
            await self.working_set.remove(user_id)
            return
        
        await state.set_server(executor.config.servers.index(target_server))

        # I love pathlib
        run_script_path : pathlib.Path = pathlib.Path(target_server.path) / self.path / "Source/run.sh"
        execution_path = run_script_path.parent
        
        # TODO
        flag = "HI"
        port = "6546"
        hostname = "127.0.0.1"

        cmd = f"cd {execution_path} && bash {run_script_path} --flag {flag} --hostname {hostname} --port {port}"
        log.info(f"  + executing command {cmd}")
        result = await executor.run(target_server, cmd)
        log.info(f"  + command resulted: {result}")

        if result is None:
            await state.set("failed", "starting run.sh failedg")
            await self.working_set.remove(user_id)
        

    async def stop(self, executor, user_id: str):

        log.info("Stopping challenge!")
        db = ChallengeState(executor.config.database, self.name, user_id)
        
        target_server = executor.config.servers[ await db.get_server() ]
        
        if target_server is None:
            await self.working_set.remove(user_id)
            log.warning("server not found, cannot stop")
            return

        port = "6546"

        destroy_script_path : pathlib.Path = pathlib.Path(target_server.path) / self.path / f"Source/destroy.sh --port {port}"
        log.info(f"  + destroy script: {destroy_script_path}")
        log.info(f"  + execution location: {execution_path}")

        execution_path = destroy_script_path.parent
        cmd = f"cd {execution_path} && bash {destroy_script_path}"

        log.info(f"  + running command: {cmd}")
        res = await executor.run(target_server, cmd)
        log.info(f"  + result: {res}")
        
        await db.delete()
        await self.working_set.remove(user_id)
        log.info(f"  + updated local state")


def parse_challenges(path: str) -> dict[str, Challenge]:
    
    sys.path.append(path)
    import checker

    set = checker.ChallengeSet(path)

    parsed_challenges = {}

    for challenge_id, challenge in set.challenges.items():
        path = challenge.path.removeprefix("/challenges/") # here is tight coupling :(    
        parsed_challenges[challenge.name] = Challenge(challenge.name, path)

    return parsed_challenges