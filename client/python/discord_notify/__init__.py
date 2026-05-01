"""
discord-notify Python client

Two usage patterns:

1. Module-level (quick one-off):
    from discord_notify import notify
    notify.success("ETL 完成", channel_id="1485916068307533937")

2. Configured instance (recommended for projects):
    from discord_notify import DiscordNotifier
    notifier = DiscordNotifier(
        default_channel_id=settings.DISCORD_NOTIFY_CHANNEL,
        project="lilium",
    )
    notifier.success("ETL 完成")
    notifier.error("失敗", channel_id=settings.DISCORD_ERROR_CHANNEL)  # override
"""
import os
import traceback
from typing import Optional

import httpx

SOCKET_PATH = os.getenv("DISCORD_NOTIFY_SOCKET", "/tmp/discord-notify.sock")


def _send(
    channel_id: str,
    level: str,
    title: str,
    body: Optional[str] = None,
    fields: Optional[dict] = None,
    file_path: Optional[str] = None,
    exc: Optional[Exception] = None,
    project: Optional[str] = None,
) -> dict:
    if exc is not None:
        tb = traceback.format_exc()
        fields = fields or {}
        fields["error"] = str(exc)[:1024]
        if tb and tb.strip() != "NoneType: None":
            body = body or tb[-2000:]

    payload: dict = {"channel_id": channel_id, "level": level, "title": title}
    if body:
        payload["body"] = body
    if fields:
        payload["fields"] = {k: str(v) for k, v in fields.items()}
    if file_path:
        payload["file_path"] = file_path
    if project:
        payload["project"] = project

    try:
        transport = httpx.HTTPTransport(uds=SOCKET_PATH)
        with httpx.Client(transport=transport, timeout=5) as client:
            r = client.post("http://localhost/notify", json=payload)
            return r.json()
    except Exception as e:
        print(f"[discord-notify] failed to send: {e}")
        return {"status": "error", "message": str(e)}


class DiscordNotifier:
    """
    Project-level notifier with a default channel.

    Usage:
        notifier = DiscordNotifier(
            default_channel_id="1485916068307533937",
            project="lilium",
        )
        notifier.success("ETL 完成", fields={"rows": "1234"})
        notifier.error("失敗", channel_id="OTHER_CHANNEL_ID")
    """

    def __init__(self, default_channel_id: str, project: Optional[str] = None):
        self.default_channel_id = default_channel_id
        self.project = project

    def _resolve(self, channel_id: Optional[str]) -> str:
        return channel_id or self.default_channel_id

    def success(self, title: str, channel_id: Optional[str] = None, **kwargs) -> dict:
        return _send(self._resolve(channel_id), "success", title, project=self.project, **kwargs)

    def error(self, title: str, channel_id: Optional[str] = None, **kwargs) -> dict:
        return _send(self._resolve(channel_id), "error", title, project=self.project, **kwargs)

    def info(self, title: str, channel_id: Optional[str] = None, **kwargs) -> dict:
        return _send(self._resolve(channel_id), "info", title, project=self.project, **kwargs)

    def warn(self, title: str, channel_id: Optional[str] = None, **kwargs) -> dict:
        return _send(self._resolve(channel_id), "warn", title, project=self.project, **kwargs)


# Module-level convenience functions (no default channel)
class _Notify:
    def success(self, title: str, channel_id: str, **kwargs) -> dict:
        return _send(channel_id, "success", title, **kwargs)

    def error(self, title: str, channel_id: str, **kwargs) -> dict:
        return _send(channel_id, "error", title, **kwargs)

    def info(self, title: str, channel_id: str, **kwargs) -> dict:
        return _send(channel_id, "info", title, **kwargs)

    def warn(self, title: str, channel_id: str, **kwargs) -> dict:
        return _send(channel_id, "warn", title, **kwargs)


notify = _Notify()
