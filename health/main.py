from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

app = FastAPI()

@app.get("/")
async def ping(request: Request):
    start_time = time.time()

    process_time = (time.time() - start_time) * 1000  # миллисекунды
    return JSONResponse(
        content={
            "status": "ok",
            "response_time_ms": round(process_time, 2)
        }
    )