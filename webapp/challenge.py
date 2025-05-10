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
    def __init__(self, name: str, path, flag) -> None:
        self.name = name
        self.path = path
        self.flag = flag
        self.url = None

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
                    if user_id in self.challenges:
                        self.challenges.remove(user_id)

        self.working_set = WorkingSet()
    
    async def parse_test_output(self, result, db_entry):
        try:
            data = json.loads(result)
        except ValueError as e:
            log.warning(f"  + pre-execution test yielded invalid JSON! results: {result}")
            await db_entry.set("failed", f"pre-flight test failed to run!")

        
        if(len(list(filter(lambda x: x != "", data.values()))) > 0):
            log.info(f"  + challenge down!")
            await db_entry.set("stopped")
        else:
            log.info("  + check OK! challenge up!")
            await db_entry.set("running")


    async def retrieve_state(self, executor, user_id: str):
        log.info(f"checking state of challenge! {self.name} {user_id}")
        state = ChallengeState(executor.config.database, self.name, user_id)
        if await state.get() is None:
            await state.create_challenge()

        async def retrieve(server):

            port = await state.get_port()
            if (port is None):
                return None
            
            hostname = "0.0.0.0"

            log.info("looking for python")
            python_path = await executor.run(server, "which python3", timeout=1)
            if(len(python_path) <= 0):
                log.critical(f"python3 is not available on {server}!")

            challenge_path = pathlib.Path(server.path) / self.path
            probe_script_path = challenge_path / "Tests/main.py"
            cmd = f"{python_path} {probe_script_path} "
            cmd += f"--connection-string \"127.0.0.1 {port}\" --flag={self.flag} "
            cmd += f"--handout-path {challenge_path / "Handout"} "
            cmd += f"--deployment-path {challenge_path / "Source"} "

            # result = await executor.run(server, cmd, timeout=1)
            result = '{"test": ""}'

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
            await state.set("stopped", "challenge not found on a server")
            return
        else:
            await self.parse_test_output(results[idx], state)

    async def start(self, executor, user_id: str):
        log.info(f"starting challenge! {self.name} {user_id}")

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
        
        log.info("  + allocating port")
        port = target_server.alloc_port()
        await state.set_port(port)

        hostname = "0.0.0.0"

        cmd = f"cd {execution_path} && bash {run_script_path} --flag '{self.flag}' --hostname {hostname} --port {port}"
        result = await executor.run(target_server, cmd, timeout=100000)
        log.info(f"  + command resulted: {result}")

        if result is None:
            await state.set("failed", "starting run.sh failed")
            await self.working_set.remove(user_id)
        

    async def stop(self, executor, user_id: str):
        log.info(f"Stopping challenge!  {self.name} {user_id}")
        state = ChallengeState(executor.config.database, self.name, user_id)
        
        target_server = executor.config.servers[ await state.get_server() ]
        
        if target_server is None:
            await self.working_set.remove(user_id)
            log.warning("server not found, cannot stop")
            return

        port = await state.get_port()

        destroy_script_path : pathlib.Path = pathlib.Path(target_server.path) / self.path / f"Source/destroy.sh --port {port}"
        execution_path = destroy_script_path.parent
        cmd = f"cd {execution_path} && bash {destroy_script_path}"
        log.info(f"  + destroy script: {destroy_script_path}")
        log.info(f"  + execution location: {execution_path}")

        res = await executor.run(target_server, cmd)
        log.info(f"  + result: {res}")
        
        await state.delete()
        await self.working_set.remove(user_id)
        log.info(f"  + updated local state")


def parse_challenges(path: str) -> dict[str, Challenge]:
    
    sys.path.append(path)
    import checker

    set = checker.ChallengeSet(path)

    parsed_challenges = {}

    for challenge_id, challenge in set.challenges.items():
        path = challenge.path.removeprefix("/challenges/") # here is tight coupling :(
        flag = list(challenge.flag.keys())[0]
        parsed_challenges[challenge.uuid] = Challenge(challenge.uuid, path, flag)
        parsed_challenges[challenge.uuid].url = challenge.url[0]

    return parsed_challenges