import tomllib

from webapp.challenge import parse_challenges
from webapp.server import parse_servers
from webapp.database import Database

from multiprocessing import Pool

from logging import getLogger

import os

log = getLogger(__name__)


class Config:
    def validate_config(self):
        
        if(not os.access(self.keyfile, os.O_RDONLY)):
            log.critical(f"cannot access/find key at: {self.keyfile}")
            return False    
        
        if(self.database is None):
            log.critical(f"failed to open database!")
            return False
        
        if(len(self.servers) <= 0):
            log.critical(f"no servers supplied! consider adding a test-server \
                         see ./test-servers/README.md")
            return False
        
        if(len(self.challenges) < 0):
            log.critical(f"failed to parse challenges from {self.challenge_path}")
            return False
        return True

    def __init__(self, config_path: str) -> None:
        self.pool = Pool()

        with open(config_path, "rb") as config:
            data = tomllib.load(config)

            self.api = data["api"]

            self.challenge_path = data["docker"]["challenge_path"]
            self.challenges = parse_challenges(self.challenge_path)

            self.keyfile = data["ssh"]["keyfile"]

            self.servers = parse_servers(data["servers"])

            self.database = Database(data["database"]["path"])

            for server in self.servers:
                server.connect(self.keyfile)
        log.debug(f"Config has been read from {config_path}!")

        assert(self.validate_config())
            
