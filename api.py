from typing import Annotated
from asyncio import create_task, Lock
from fastapi import FastAPI, HTTPException, status, Path
from database import ChallengeState
from json import dumps

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

    await challenge.retrieve_state(executor, user_id)

    state = await ChallengeState(app.extra["config"].database, service_name, user_id).get()
    if state is not None:
        if state == "running":
            return {"running"}

    if await challenge.working_set.contains_or_insert(user_id):
        task = create_task(challenge.start(executor, user_id))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
        return {"starting"}
    else:
        return {"still working on it"}

@app.get("/stop/{user_id}/{service_name}")
async def stop_challenge(
        user_id: Annotated[str, Path(pattern=ALPHANUM)], 
        service_name: Annotated[str, Path(pattern=ALPHANUM)]):
    does_challenge_exist(app, service_name)
    executor = app.extra["executor"]
    challenge = app.extra["config"].challenges[service_name]
    await challenge.retrieve_state(executor, user_id)

    state = await ChallengeState(app.extra["config"].database, service_name, user_id).get()
    if state is not None:
        if state != "running":
            return {"not running"}

    if await challenge.working_set.contains_or_insert(user_id):
        task = create_task(challenge.stop(executor, user_id))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
        return {"stopping"}
    else:
        return {"still working on it"}


@app.get("/status/{user_id}/{service_name}")
async def challenge_status(
        user_id: Annotated[str, Path(pattern=ALPHANUM)], 
        service_name: Annotated[str, Path(pattern=ALPHANUM)]):
    does_challenge_exist(app, service_name)

    executor = app.extra["executor"]
    challenge = app.extra["config"].challenges[service_name]

    await challenge.retrieve_state(executor, user_id)
    state = await ChallengeState(app.extra["config"].database, service_name, user_id).get_with_reason()
    r = {
        "state": 'not started',
    }
    if state is not None:
        state, reason = state
        r['state'] = state
        if state == "running":
            r['port'] = reason
        if state == "failed":
            r['reason'] = reason
    return r
