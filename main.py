from config import Config
from executor import Executor
from api import app
from uvicorn import run
import logging

def main():
    logging.basicConfig(level=logging.INFO)

    config = Config("config.toml")

    executor = Executor(config)
    executor.create_enviroment()

    run(app, host=config.api["ip"], port=config.api["port"])

if __name__ == "__main__":
    main()
