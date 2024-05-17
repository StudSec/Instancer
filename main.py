import asyncio
from webapp.config import Config
from webapp.executor import Executor
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
from webapp.api import app
import logging


async def server(config, executor):
    await executor.create_enviroment()

    async def update_challenges():
        while True:
            try:
                await asyncio.sleep(60 * 5)
                await executor.create_enviroment()
            except Exception as e:
                log = logging.getLogger(__name__)
                log.warning(f"Something went wrong while creating environment: {e}")

    app.extra = {
        "config": config,
        "executor": executor
    }

    hypercorn = HypercornConfig()
    hypercorn.bind = [f"{config.api['ip']}:{config.api['port']}"]
    await asyncio.gather(
        serve(app, hypercorn),
        update_challenges()
    )


def main():
    logging.basicConfig(level=logging.INFO)

    config = Config("config.toml")

    executor = Executor(config)

    asyncio.run(server(config, executor))


if __name__ == "__main__":
    main()
