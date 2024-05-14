import asyncio
from config import Config
from executor import Executor
from api import app
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
import logging


def main():
    logging.basicConfig(level=logging.INFO)

    config = Config("config.toml")

    executor = Executor(config)
    executor.create_enviroment()

    hypercorn = HypercornConfig()
    hypercorn.bind = [f"{config.api['ip']}:{config.api['port']}"]
    asyncio.run(serve(app, hypercorn))


if __name__ == "__main__":
    main()
