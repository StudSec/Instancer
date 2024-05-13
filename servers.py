import tomllib
from logging import warning

class Server:
    def __init__(self, hostname, ip, port, user):
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.user = user
        pass

def read_servers():
    with open("config.toml", "rb") as config:
        data = tomllib.load(config)
        hosts = data["servers"]
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

print(read_servers())

# docker-compose -p [team name] up -d powerpc
# docker-compose -p [team name] port powerpc 5000
