import asyncio
from config import Config
from executor import Executor
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
from api import app
import logging

def main():
    logging.basicConfig(level=logging.INFO)

    config = Config("config.toml")

    executor = Executor(config)
    # executor.create_enviroment()

    app.extra = {
        "config": config,
        "executor": executor
    }

    hypercorn = HypercornConfig()
    hypercorn.bind = [f"{config.api["ip"]}:{config.api["port"]}"]
    asyncio.run(serve(app, hypercorn))

if __name__ == "__main__":
    main()
