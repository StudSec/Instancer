from config import Config

def main():
    config = Config("config.toml")
    print(config)

    servers = config.servers
    print(servers.load())

if __name__ == "__main__":
    main()
