import asyncio
import json
import sys
from pathlib import Path

import httpx
import redis.asyncio as aioredis

sys.path.insert(0, str(Path(__file__).parent.parent))
from common.config import BOT_TOKEN, DEAD_LETTER_KEY, QUEUE_KEY, REDIS_URL

DISCORD_API = "https://discord.com/api/v10"

LEVEL_COLORS = {
    "success": 0x57F287,
    "error":   0xED4245,
    "warn":    0xFEE75C,
    "info":    0x5865F2,
}

LEVEL_EMOJI = {
    "success": "✅",
    "error":   "❌",
    "warn":    "⚠️",
    "info":    "ℹ️",
}


def build_embed(payload: dict) -> dict:
    level = payload.get("level", "info")
    embed: dict = {
        "title": f"{LEVEL_EMOJI.get(level, '')} {payload['title']}",
        "color": LEVEL_COLORS.get(level, 0x5865F2),
    }
    if payload.get("body"):
        embed["description"] = payload["body"][:4096]
    if payload.get("fields"):
        embed["fields"] = [
            {"name": k, "value": str(v)[:1024], "inline": True}
            for k, v in payload["fields"].items()
        ]
    return embed


async def send_to_discord(payload: dict) -> bool:
    channel_id = payload["channel_id"]
    embed = build_embed(payload)
    url = f"{DISCORD_API}/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}

    async with httpx.AsyncClient(timeout=15) as client:
        file_path = payload.get("file_path")
        if file_path:
            path = Path(file_path)
            if path.exists():
                files = {"file": (path.name, path.read_bytes())}
                data = {"payload_json": json.dumps({"embeds": [embed]})}
                r = await client.post(url, headers=headers, data=data, files=files)
            else:
                print(f"[sender] file not found: {file_path}, sending without attachment")
                r = await client.post(url, headers=headers, json={"embeds": [embed]})
        else:
            r = await client.post(url, headers=headers, json={"embeds": [embed]})

    if r.status_code not in (200, 201):
        print(f"[sender] Discord API error {r.status_code}: {r.text[:200]}")
        return False
    return True


async def process_with_retry(payload: dict, redis_client: aioredis.Redis) -> None:
    job_id = payload.get("id", "?")
    for attempt in range(3):
        try:
            if await send_to_discord(payload):
                print(f"[sender] sent {job_id} ({payload.get('title', '')[:50]})")
                return
        except Exception as e:
            print(f"[sender] attempt {attempt + 1}/3 failed for {job_id}: {e}")

        if attempt < 2:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s

    # All retries failed → dead letter
    await redis_client.rpush(DEAD_LETTER_KEY, json.dumps(payload))
    print(f"[sender] dead letter: {job_id} ({payload.get('title', '')[:50]})")


async def run():
    redis_client = aioredis.from_url(REDIS_URL)
    print("[sender] worker started")
    while True:
        try:
            result = await redis_client.blpop(QUEUE_KEY, timeout=0)
            if result:
                _, raw = result
                payload = json.loads(raw)
                asyncio.create_task(process_with_retry(payload, redis_client))
        except Exception as e:
            print(f"[sender] queue error: {e}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run())
