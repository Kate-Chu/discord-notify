from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Level(str, Enum):
    info = "info"
    success = "success"
    error = "error"
    warn = "warn"


class NotifyRequest(BaseModel):
    channel_id: str
    level: Level = Level.info
    title: str
    body: Optional[str] = None
    fields: Optional[dict[str, str]] = None
    file_path: Optional[str] = None
    project: Optional[str] = None  # optional, for logging only
