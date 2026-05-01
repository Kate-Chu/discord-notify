# discord-notify

A lightweight self-hosted Discord notification gateway. Projects POST a message to the local Unix socket; the gateway queues it in Redis and a sender worker delivers it to Discord.

## Architecture

```
Caller (Python / TypeScript / shell)
    │  POST { channel_id, level, title, ... }
    ▼
[Gateway - FastAPI, Unix socket]
    ▼
[Redis DB1]
    ▼
[Sender Worker - retry 3x]
    ▼
Discord API (bot token)
```

- Gateway and sender run in the same process (`start.py`)
- Unix socket only — no exposed TCP port
- Redis DB1 — isolated from other services using DB0
- Callers decide the target channel; the gateway does no routing

---

## Requirements

- Python 3.11+
- Redis

---

## Setup

```bash
git clone https://github.com/your-username/discord-notify.git
cd discord-notify

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.template .env
# fill in DISCORD_BOT_TOKEN
```

### .env

```env
DISCORD_BOT_TOKEN=your_bot_token_here
REDIS_URL=redis://localhost:6379/1
SOCKET_PATH=/tmp/discord-notify.sock
```

---

## Run

```bash
python start.py
```

Both gateway and sender start together:
```
INFO:     Uvicorn running on unix socket /tmp/discord-notify.sock
[sender] worker started
Gateway started
```

### Quick test

```bash
curl --unix-socket /tmp/discord-notify.sock \
  -X POST http://localhost/notify \
  -H 'Content-Type: application/json' \
  -d '{"channel_id":"YOUR_CHANNEL_ID","level":"success","title":"test"}'
```

---

## Deploy

### macOS (LaunchAgent)

```bash
cp deploy/discord-notify.plist ~/Library/LaunchAgents/com.yourname.discord-notify.plist
# edit the plist to set the correct python path
launchctl load ~/Library/LaunchAgents/com.yourname.discord-notify.plist
```

Check status:
```bash
launchctl list | grep discord-notify
```

Log: `/tmp/discord-notify.log`

Stop / restart:
```bash
launchctl unload ~/Library/LaunchAgents/com.yourname.discord-notify.plist
launchctl load   ~/Library/LaunchAgents/com.yourname.discord-notify.plist
```

### Linux (systemd)

```bash
sudo cp deploy/discord-notify.service /etc/systemd/system/
# edit the service file to set the correct user and python path
sudo systemctl daemon-reload
sudo systemctl enable discord-notify
sudo systemctl start discord-notify
```

Check status:
```bash
sudo systemctl status discord-notify
journalctl -u discord-notify -f
```

Update:
```bash
git pull && sudo systemctl restart discord-notify
```

---

## Client Usage

### Python

Install:
```bash
pip install git+https://github.com/your-username/discord-notify.git#subdirectory=client/python
```

**DiscordNotifier (recommended for project-level use)**

```python
from discord_notify import DiscordNotifier

notifier = DiscordNotifier(
    default_channel_id=settings.DISCORD_NOTIFY_CHANNEL,
    project="my-project",
)

notifier.success("ETL complete", fields={"rows": "1234", "duration": "12s"})
notifier.error("DB error", exc=some_exception)
notifier.info("Backup done", file_path="/tmp/report.csv")

# override channel per call
notifier.error("Critical", channel_id=settings.DISCORD_ERROR_CHANNEL)
```

**Module-level (quick one-off)**

```python
from discord_notify import notify

notify.success("done", channel_id="YOUR_CHANNEL_ID")
notify.error("failed", channel_id="YOUR_CHANNEL_ID", body="error message")
```

### Django

**Auto-send ERROR logs to Discord:**

```python
# settings.py
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "discord": {
            "class": "discord_notify.django.DiscordLogHandler",
            "channel_id": env("DISCORD_ERROR_CHANNEL"),
            "project": "my-project",
        }
    },
    "root": {"handlers": ["discord"], "level": "ERROR"},
}
```

**Management command auto-report:**

```python
from discord_notify.django import report_to_discord

@report_to_discord(channel_id=settings.DISCORD_NOTIFY_CHANNEL, project="my-project")
class Command(BaseCommand):
    def handle(self, *args, **options):
        ...  # auto sends success on completion, error + traceback on exception
```

### TypeScript

Copy `client/typescript/discord-notify.ts` directly into your project — no npm package needed.

```typescript
import { DiscordNotifier } from './discord-notify'

const notifier = new DiscordNotifier(
  process.env.DISCORD_NOTIFY_CHANNEL!,
  'my-project'
)

await notifier.success('Sync complete', { body: '42 events added' })
await notifier.error('Sync failed', { body: err.message })

// override channel
await notifier.error('Critical', { channel_id: process.env.DISCORD_ERROR_CHANNEL })
```

### Shell

```bash
curl --unix-socket /tmp/discord-notify.sock \
  -X POST http://localhost/notify \
  -H 'Content-Type: application/json' \
  -d '{
    "channel_id": "YOUR_CHANNEL_ID",
    "level": "info",
    "title": "Backup complete"
  }'
```

---

## Message Schema

| Field | Required | Description |
|---|---|---|
| `channel_id` | ✅ | Discord channel ID — decided by the caller |
| `level` | | `info` / `success` / `error` / `warn` (default: `info`) |
| `title` | ✅ | Message title |
| `body` | | Description text (max 4096 chars) |
| `fields` | | `{"key": "value"}` rendered as embed fields |
| `file_path` | | Absolute path — gateway reads and attaches the file |
| `project` | | Source identifier, used for logging only |

---

## Dead Letter

Messages that fail after 3 retries are pushed to a Redis dead letter list:

```bash
redis-cli -n 1 lrange discord_gateway:dead_letter 0 -1
```

---

## Project Layout

```
discord-notify/
├── start.py              # single entrypoint: gateway + sender
├── requirements.txt
├── common/
│   ├── models.py         # pydantic schema
│   └── config.py         # .env loader
├── gateway/main.py       # FastAPI, POST /notify
├── sender/worker.py      # BLPOP → Discord API → retry
├── client/
│   ├── python/discord_notify/
│   │   ├── __init__.py   # DiscordNotifier, notify
│   │   └── django.py     # DiscordLogHandler, @report_to_discord
│   └── typescript/discord-notify.ts
└── deploy/
    ├── discord-notify.plist    # macOS LaunchAgent template
    └── discord-notify.service  # Linux systemd template
```
