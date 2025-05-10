from typing import Annotated
from asyncio import create_task
from fastapi import FastAPI, HTTPException, status, Path, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from webapp.database import ChallengeState
from logging import getLogger
import traceback as tb

log = getLogger(__name__)

app = FastAPI()

security = HTTPBasic()

background_tasks = set()

ALPHANUM = r"^[a-z0-9\-_]*$"


def does_challenge_exist(app: FastAPI, service_name: str):
    challenges = app.extra["config"].challenges
    if service_name not in challenges:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{service_name}' not found"
        )


def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = app.extra["config"].api["username"]
    password = app.extra["config"].api["password"]

    if credentials.username != username or credentials.password != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/start/{user_id}/{service_name}")
async def start_challenge(
        user_id: Annotated[str, Path(pattern=ALPHANUM)],
        service_name: Annotated[str, Path(pattern=ALPHANUM)],
        username: str = Depends(authenticate),
        ):
    try:
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
    except HTTPException as e:
        return {e.detail}
    except Exception as e:
        log.warning(f"Error occured in start API: {tb.format_exc()}")
        return {"something went wrong"}


@app.get("/stop/{user_id}/{service_name}")
async def stop_challenge(
        user_id: Annotated[str, Path(pattern=ALPHANUM)],
        service_name: Annotated[str, Path(pattern=ALPHANUM)],
        username: str = Depends(authenticate),
        ):
    try:
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
    except HTTPException as e:
        return {e.detail}
    except Exception as e:
        log.warning(f"Error occured in stop API: {tb.format_exc()}")
        return {"something went wrong"}


@app.get("/status/{user_id}/{service_name}")
async def challenge_status(
        user_id: Annotated[str, Path(pattern=ALPHANUM)],
        service_name: Annotated[str, Path(pattern=ALPHANUM)],
        username: str = Depends(authenticate),
        ):
    try:
        does_challenge_exist(app, service_name)

        executor = app.extra["executor"]
        challenge = app.extra["config"].challenges[service_name]

        await challenge.retrieve_state(executor, user_id)
        state = await ChallengeState(app.extra["config"].database, service_name, user_id).get_with_reason()
        r = {
            "state": 'not started',
        }
        if state is not None:
            port = await ChallengeState(app.extra["config"].database, service_name, user_id).get_port()
            server = executor.config.servers[ await ChallengeState(app.extra["config"].database, service_name, user_id).get_server() ]
            state, reason = state
            r['state'] = state
            if state == "running":
                r['url'] = challenge.url.replace("{{PORT}}", str(port)).replace("{{IP}}", server.ip)
            if state == "failed":
                r['reason'] = reason
        return r
    except HTTPException as e:
        return {e.detail}
    except Exception as e:
        log.warning(f"Error occured in status API: {tb.format_exc()}")
        return {"state": "failed", "reason": "something went wrong"}
