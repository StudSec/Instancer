import tomllib

from challenge import parse_compose
from server import parse_servers
from multiprocessing import Pool

class Config:
    def __init__(self, config_path: str) -> None:
        self.pool = Pool()

        with open(config_path, "rb") as config:
            data = tomllib.load(config)

            self.compose_path = data["docker"]["compose_path"]
            self.challenges = parse_compose(self.compose_path)

            self.keyfile = data["ssh"]["keyfile"]

            self.servers = parse_servers(data["servers"])
            for server in self.servers:
                server.connect(self.keyfile)
