import json
import sys
from pathlib import Path
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).parent.parent))
from common.config import QUEUE_KEY, REDIS_URL
from common.models import NotifyRequest

app = FastAPI()
redis_client: aioredis.Redis | None = None


@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = aioredis.from_url(REDIS_URL)
    print("Gateway started")


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.aclose()


@app.post("/notify")
async def notify(req: NotifyRequest):
    job_id = str(uuid4())
    payload = req.model_dump()
    payload["id"] = job_id
    payload["level"] = req.level.value

    await redis_client.rpush(QUEUE_KEY, json.dumps(payload))
    print(f"[gateway] queued {job_id} → channel {req.channel_id} ({req.project or '-'})")
    return {"status": "queued", "id": job_id}


@app.get("/health")
async def health():
    return {"status": "ok"}
