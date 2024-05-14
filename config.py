import tomllib

from challenge import parse_compose
from server import parse_servers
from multiprocessing import Pool

from logging import getLogger

log = getLogger(__name__)


class Config:
    def __init__(self, config_path: str) -> None:
        self.pool = Pool()

        with open(config_path, "rb") as config:
            data = tomllib.load(config)

            self.api = data["api"]

            self.compose_path = data["docker"]["compose_path"]
            self.challenges = parse_compose(self.compose_path)

            self.keyfile = data["ssh"]["keyfile"]

            self.servers = parse_servers(data["servers"])

            for server in self.servers:
                server.connect(self.keyfile)
        log.debug(f"Config has been read from {config_path}!")
