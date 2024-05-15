from fastapi import FastAPI, HTTPException, status

app = FastAPI()

@app.get("/start/{user_id}/{service_name}")
async def start_challenge(user_id: str, service_name: str):
    challenges = app.extra["config"].challenges
    if service_name not in challenges:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{service_name}' not found"
        )

    await app.extra["executor"].get_available_server()
    
    return {service_name}

@app.get("/stop/{user_id}/{service_name}")
async def stop_challenge(user_id: str, service_name: str):
    return {user_id}

@app.get("/status/{user_id}/{challenge_id}")
async def challenge_status(user_id: str, service_name: str):
    return {user_id}
