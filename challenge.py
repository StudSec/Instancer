from yaml import safe_load
from logging import getLogger
log = getLogger(__name__)

class Challenge:
    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self._config = config

        self.ports = list()
        for port in config["ports"]:
            self.ports.append(Port(name, port))

        r = "Make sure you use resource limits on each service to prevent resource exhaustion!"
        if "deploy" not in config:
            log.warning(f"No deploy label for {name}. {r}")
        else:
            if "resources" not in config["deploy"]:
                log.warning(f"No resource label in deploy section of {name}. {r}")
            else:
                if "limits" not in config["deploy"]["resources"]:
                    log.warning(f"No limits label in resources of {name}. {r}")

class Port:
    def __init__(self, challenge_name: str, ports: str) -> None:
        proto = ports.split("/")
        if len(proto) == 1:
            self.proto = None
        else:
            self.proto = proto[1]


        parts = proto[0].split(":")
        if len(parts) != 1:
            log.warning(f"Hardcoded port on the host specified in '{ports}' for challenge {challenge_name}, " +
                    "WILL cause problems when deploying and running out of ports")
        self.port = parts[-1]


def parse_compose(path: str) -> dict[str, Challenge]:
    with open(path) as f:
        data = safe_load(f)
        services = data["services"]

        challenges = dict()
        for name in services:
            config = services[name]

            # Only challenges with exposed ports are treated as challenges
            if "ports" in config:
                challenge = Challenge(name, services[name])
                challenges[name] = challenge

        return challenges
