#!/usr/bin/python3
from webapp.api import app  # Replace 'your_app_name' with the name of your FastAPI app file
from fastapi.testclient import TestClient
import fastapi.security
import httpx
import tomllib
import asyncio
from webapp.executor import Executor
from webapp.config import Config

CONFIG_PATH = "config.toml"

def get_config():
    with open(CONFIG_PATH, "rb") as config:
        data = tomllib.load(config)
    return data

def get_authentication():
    config = get_config()
    print(f"username = {config["api"]["username"]} & password = {config["api"]["password"]}")
    return httpx.BasicAuth(config["api"]["username"], config["api"]["password"])


client = TestClient(app)
config = Config(CONFIG_PATH)
executor = Executor(config)


asyncio.run(executor.create_enviroment())

app.extra = {
    "config": config,
    "executor": executor
}



def test_start_stop_status_endpoints(): 
    user_id = "12345"  # Arbitrary user ID
    service_name = "buffer_overflow"
    
    auth = get_authentication()
    
    response = client.get(f"/start/{user_id}/{service_name}", auth=auth)
    assert response.status_code == 200

    response = client.get(f"/status/{user_id}/{service_name}", auth=auth)
    assert response.status_code == 200
    
    response = client.get(f"/stop/{user_id}/{service_name}", auth=auth)
    assert response.status_code == 200
    # Add specific assertions here as well
    # assert response.json() == {"message": "Service stopped successfully"}
