from fabric import Connection
from logging import getLogger

log = getLogger(__name__)

END_PORT_RANGE = 65535
START_PORT_RANGE = 1024


class Server:
    def __init__(self, hostname, ip, port, user, path):
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.user = user
        self.path = path
        self.portlist = set()
        self.last_alloced_port = START_PORT_RANGE
        self.connection = None    

    def connect(self, keyfile: str):
        self.connection = Connection(f"{self.user}@{self.ip}:{self.port}", connect_kwargs={
            "key_filename": keyfile
        })
    
    def increment_port(self):
        self.last_alloced_port += 1
        if self.last_alloced_port >= END_PORT_RANGE:
            self.last_alloced_port = START_PORT_RANGE
        return self.last_alloced_port
    
    def alloc_port(self):
        self.last_alloced_port = self.increment_port()
        
        while self.last_alloced_port in self.portlist:
            self.increment_port()
        
        self.portlist.add(self.last_alloced_port)
        return self.last_alloced_port

    def free_port(self, port):
        if port in self.portlist:
            log.warning(f"free_port: double free detected on port {port}")
        self.portlist.remove(port)


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
