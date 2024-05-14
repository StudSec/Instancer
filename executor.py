import asyncio
from config import Config
from shlex import quote
from os.path import join, dirname, basename
from logging import getLogger
from tempfile import NamedTemporaryFile
from shutil import make_archive

log = getLogger(__name__)

def setup_env(server, tar):
    server.connection.run(f"rm -rf {quote(server.path)}")
    server.connection.run(f"mkdir -p {quote(server.path)}")

    to_path = join(server.path, basename(tar))
    log.info(f"[{server.hostname}]\tputting {tar} to {to_path}")
    server.connection.put(tar, to_path)

    extract_cmd = f"tar -xf {quote(to_path)} --directory {quote(server.path)}"
    log.info(f"[{server.hostname}]\tRunning {extract_cmd}")
    server.connection.run(extract_cmd)

    server.connection.run(f"rm -f {quote(to_path)}")


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

    async def current_compose_projects(self):
        def request_projects(server):
            cmd = "docker compose ls --format json"
            try:
                result = server.connection.run(cmd, hide=True)
                return result.stdout.strip()
            except Exception as e:
                log.warning(f"[{server.hostname}]\tFailed to run '{cmd}': {e}")

        print(await asyncio.gather(
            *[asyncio.to_thread(request_projects, server) for server in self.config.servers]
        ))

    async def current_challenges(self):
        pass

    async def start_challenge(self, user_id, challenge_name):
        pass

    async def stop_challenge(self, user_id, challenge_name):
        pass

    async def challenge_status(self, user_id, challenge_name):
        pass

