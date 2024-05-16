import asyncio
from config import Config
from shlex import quote
from os.path import join, dirname, basename
from logging import getLogger
from tempfile import NamedTemporaryFile
from shutil import make_archive
from server import Server

log = getLogger(__name__)

def setup_env(server, tar):
    try:
        server.connection.run(f"rm -rf {quote(server.path)}")
        server.connection.run(f"mkdir -p {quote(server.path)}")

        to_path = join(server.path, basename(tar))
        log.info(f"[{server.hostname}]\tputting {tar} to {to_path}")
        server.connection.put(tar, to_path)

        extract_cmd = f"tar -xf {quote(to_path)} --directory {quote(server.path)}"
        log.info(f"[{server.hostname}]\tRunning {extract_cmd}")
        server.connection.run(extract_cmd)

        server.connection.run(f"rm -f {quote(to_path)}")
    except Exception as e:
        log.warn(f"[{server.hostname}] Failed to setup server: {e}")

def runner(server, cmd, timeout = None) -> tuple[Server, str | None]:
    try:
        log.info(f"[{server.hostname}]\tRunning command '{cmd}'")
        result = server.connection.run(cmd, hide=True, timeout=timeout)
        return (server, result.stdout.strip())
    except Exception as e:
        log.warning(f"[{server.hostname}]\tFailed to run '{cmd}': {e}")
        return (server, None)

class Executor:
    def __init__(self, config: Config):
        self.config = config

    def create_enviroment(self):
        # List all the files that have to be uploaded
        base_dir = dirname(self.config.compose_path)

        with NamedTemporaryFile(delete_on_close=False) as f:
            log.info(f"Making archive of {base_dir}")
            archive_name = make_archive(
                f.name,
                "tar",
                base_dir)

            log.info(f"Sending archive to {len(self.config.servers)} servers")
            self.config.pool.starmap(setup_env, [(server, archive_name) for server in self.config.servers])

    async def run_all(self, cmd, timeout = None) -> list[tuple[Server, str]]:
        result = await asyncio.gather(
            *[asyncio.to_thread(runner, server, cmd, timeout) for server in self.config.servers]
        )
        return [(server, response) for (server, response) in result if response != None]

    async def run(self, server, cmd, timeout = None) -> str | None:
        _, result = await asyncio.to_thread(runner, server, cmd, timeout)
        return result

    #async def current_compose_projects(self):
    #    await self.run_all("docker compose ls --format json")

    async def get_available_server(self) -> Server | None:
        loads = await self.run_all("cat /proc/loadavg | awk '{ print $1}'")

        if len(loads) == 0:
            return None

        (idlest_server, _) = min(loads, key = lambda l : l[1])
        return idlest_server

    async def current_challenges(self):
        pass
