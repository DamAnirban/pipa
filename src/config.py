"""
config.py
All secrets and paths in one place.
Fill in real values via environment variables — never hardcode secrets here.

Set these in /etc/systemd/system/pipa.service [Service] section (via EnvironmentFile),
or export them in your shell for manual testing. See credentials/.env.example.
"""

import os

# ── Identity ──────────────────────────────────────────────────────────────────
BOT_NAME = os.environ.get("BOT_NAME", "PiPA")

# IANA timezone name (e.g. "America/New_York", "Europe/London", "Asia/Kolkata")
TIMEZONE = os.environ.get("TIMEZONE", "UTC")

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN",  "YOUR_TELEGRAM_BOT_TOKEN")
YOUR_CHAT_ID    = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY")

# ── Google Calendar OAuth ─────────────────────────────────────────────────────
# credentials.json.example shows the client-secret shape; token.json is
# generated once by scripts/oauth_setup.py, then auto-refreshed
SRC_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)

CREDENTIALS_PATH  = os.path.join(ROOT_DIR, "credentials", "credentials.json")
GOOGLE_TOKEN_PATH = os.path.join(ROOT_DIR, "credentials", "token.json")

# ── Memory file paths ─────────────────────────────────────────────────────────
STATIC_MEMORY_PATH  = os.path.join(ROOT_DIR, "memory", "static_memory.md")
DYNAMIC_MEMORY_PATH = os.path.join(ROOT_DIR, "memory", "dynamic_memory.md")
