from logging import getLogger
log = getLogger(__name__)

class Port:
    def __init__(self, challenge_name: str, ports: str) -> None:
        ports = str(ports)
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
