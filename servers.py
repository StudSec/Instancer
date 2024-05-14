from fabric import ThreadingGroup
from fabric.exceptions import GroupException

from logging import warning

class Server:
    def __init__(self, hostname, ip, port, user):
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.user = user
        pass

    def connection_str(self) -> str:
        return f"{self.user}@{self.ip}:{self.port}"


def parse_servers(hosts):
    servers = list()
    for hostname in hosts:
        host = hosts[hostname]

        if 'ip' not in host:
            warning(f"host {hostname} is missing ip, skipping...")
            continue

        port = 22
        if 'port' in host:
            port = int(host['port'])

        user = "root"
        if 'user' in host:
            user = str(host['user'])

        servers.append(Server(hostname, host['ip'], port, user))
    return servers

# docker-compose -p [team name] up -d powerpc
# docker-compose -p [team name] port powerpc 5000

class Servers(ThreadingGroup):
    def __init__(self, servers: list[Server]):
        connection_strings = [server.connection_str() for server in servers]
        super().__init__(*connection_strings)

    def load(self):
        try:
            self.run("uptime");
        except GroupException as e:
            warning(f"Failed to get load: {e}")

