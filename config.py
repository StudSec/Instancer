import tomllib

from challenge import parse_compose
from servers import parse_servers, Servers


class Config:
    def __init__(self, config_path: str) -> None:
        with open(config_path, "rb") as config:
            data = tomllib.load(config)
            self.challenges = parse_compose(data["docker"]["compose_path"])

            self._servers = parse_servers(data["servers"])
            self.servers = Servers(self._servers)
