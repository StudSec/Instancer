from config import Config
from executor import Executor
import logging

def main():
    logging.basicConfig(level=logging.INFO)

    config = Config("config.toml")

    executor = Executor(config)
    executor.create_enviroment()

if __name__ == "__main__":
    main()
