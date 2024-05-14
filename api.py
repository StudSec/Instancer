from fastapi import FastAPI

app = FastAPI()

@app.get("/start/{challenge_id}")
async def start_challenge(challenge_id: int):
    return {challenge_id}

@app.get("/stop/{challenge_id}")
async def stop_challenge(challenge_id: int):
    return {challenge_id}

@app.get("/status/{challenge_id}")
async def challenge_status(challenge_id: int):
    return {challenge_id}
