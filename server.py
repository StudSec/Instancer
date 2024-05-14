from fabric import Connection
from logging import getLogger
log = getLogger(__name__)

class Server:
    def __init__(self, hostname, ip, port, user, path):
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.user = user
        self.path = path
        self.connection = None

    def connect(self, keyfile: str):
        self.connection = Connection(f"{self.user}@{self.ip}:{self.port}", connect_kwargs = {
            "key_filename": keyfile
        })


def parse_servers(hosts):
    servers = list()

    default = hosts["default"]

    for hostname in hosts:
        if hostname == "default":
            continue

        host = hosts[hostname]

        if 'ip' not in host:
            log.warning(f"host {hostname} is missing ip, skipping...")
            continue

        port = default["port"]
        if 'port' in host:
            port = int(host['port'])

        user = default["user"]
        if 'user' in host:
            user = str(host['user'])

        path = default["path"]
        if 'path' in host:
            path = str(host['path'])

        servers.append(Server(hostname, host['ip'], port, user, path))
    return servers

# docker-compose -p [team name] up -d powerpc
# docker-compose -p [team name] port powerpc 5000
