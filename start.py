"""
Single entrypoint: starts gateway (FastAPI) and sender worker together
in the same asyncio event loop.

Usage:
    python start.py
"""
import asyncio
import uvicorn
from sender.worker import run as run_sender
from common.config import SOCKET_PATH


async def main():
    config = uvicorn.Config(
        "gateway.main:app",
        uds=SOCKET_PATH,
        log_level="info",
    )
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        run_sender(),
    )


if __name__ == "__main__":
    asyncio.run(main())
