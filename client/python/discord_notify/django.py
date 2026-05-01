"""
Django integrations for discord-notify.

1. DiscordLogHandler — add to LOGGING to auto-send ERROR logs to Discord
2. @report_to_discord — decorator for management commands

Example settings.py:
    LOGGING = {
        "version": 1,
        "handlers": {
            "discord": {
                "class": "discord_notify.django.DiscordLogHandler",
                "channel_id": env("DISCORD_ERROR_CHANNEL"),
            }
        },
        "root": {"handlers": ["discord"], "level": "ERROR"},
    }

Example management command:
    from discord_notify.django import report_to_discord

    @report_to_discord(channel_id=settings.DISCORD_NOTIFY_CHANNEL)
    class Command(BaseCommand):
        def handle(self, *args, **options):
            ...
"""
import functools
import logging
import time
import traceback

from . import _send


class DiscordLogHandler(logging.Handler):
    def __init__(self, channel_id: str, project: str = None):
        super().__init__()
        self.channel_id = channel_id
        self.project = project

    def emit(self, record: logging.LogRecord):
        try:
            title = f"{record.name}: {record.getMessage()}"[:100]
            fields = {"logger": record.name, "level": record.levelname}

            body = None
            if record.exc_info:
                body = "".join(traceback.format_exception(*record.exc_info))[-2000:]

            _send(
                channel_id=self.channel_id,
                level="error",
                title=title,
                body=body,
                fields=fields,
                project=self.project,
            )
        except Exception:
            self.handleError(record)


def report_to_discord(channel_id: str, project: str = None):
    """
    Decorator for Django management Command classes.
    Sends success/error notification when the command finishes.

    Usage:
        @report_to_discord(channel_id=settings.DISCORD_NOTIFY_CHANNEL)
        class Command(BaseCommand):
            def handle(self, *args, **options):
                ...
    """
    def decorator(cls):
        original_handle = cls.handle

        @functools.wraps(original_handle)
        def new_handle(self, *args, **options):
            command_name = cls.__module__.split(".")[-1]
            start = time.time()
            try:
                result = original_handle(self, *args, **options)
                duration = f"{time.time() - start:.1f}s"
                _send(
                    channel_id=channel_id,
                    level="success",
                    title=f"{command_name} 完成",
                    fields={"duration": duration},
                    project=project,
                )
                return result
            except Exception as e:
                _send(
                    channel_id=channel_id,
                    level="error",
                    title=f"{command_name} 失敗",
                    exc=e,
                    project=project,
                )
                raise

        cls.handle = new_handle
        return cls

    return decorator
