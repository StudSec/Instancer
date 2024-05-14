from config import Config
from shlex import quote
from git import Git
from os.path import join, dirname
from logging import getLogger

log = getLogger(__name__)

def project_files(base_dir: str):
    g = Git(base_dir)
    return g.ls_files().splitlines()

def setup_env(server, base_dir, files):
    server.connection.run(f"rm -rf {quote(server.path)}")
    server.connection.run(f"mkdir -p {quote(server.path)}")
    for file in files:
        from_path = join(base_dir, file)
        to_path = join(server.path, file)
        log.info(f"[{server.hostname}]\tUploading '{from_path}' to '{to_path}'")
        server.connection.run(f"mkdir -p {quote(join(server.path, dirname(file)))}")
        server.connection.put(from_path, to_path)


class Executor:
    def __init__(self, config: Config):
        self.config = config

    def create_enviroment(self):
        # List all the files that have to be uploaded
        base_dir = dirname(self.config.compose_path)
        files = project_files(base_dir)

        log.info(f"Found {len(files)} project files")
        self.config.pool.starmap(setup_env, [(server, base_dir, files) for server in self.config.servers])
