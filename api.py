from typing import Annotated
from asyncio import create_task
from fastapi import FastAPI, HTTPException, status, Path

app = FastAPI()
background_tasks = set()

ALPHANUM = "^[a-zA-Z0-9_]*$"

def does_challenge_exist(app: FastAPI, service_name: str):
    challenges = app.extra["config"].challenges
    if service_name not in challenges:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{service_name}' not found"
        )

@app.get("/start/{user_id}/{service_name}")
async def start_challenge(
        user_id: Annotated[str, Path(pattern=ALPHANUM)], 
        service_name: Annotated[str, Path(pattern=ALPHANUM)]):

    does_challenge_exist(app, service_name)

    executor = app.extra["executor"]
    challenge = app.extra["config"].challenges[service_name]

    task = create_task(challenge.start(executor, user_id))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    return {"ok"}

@app.get("/stop/{user_id}/{service_name}")
async def stop_challenge(user_id: str, service_name: str):
    return {user_id}

@app.get("/status/{user_id}/{challenge_id}")
async def challenge_status(user_id: str, service_name: str):
    return {user_id}
