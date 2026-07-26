"""
PiPA — Personal Assistant Bot
Runs on a Raspberry Pi (or any always-on machine). Handles incoming Telegram
messages and proactive pings (triggered by cron). Two-way with Claude API + calendar.

Usage:
  python3 src/bot.py                   # starts the listener (keep running)
  python3 src/bot.py --ping morning
  python3 src/bot.py --ping midday
  python3 src/bot.py --ping pre_focus
  python3 src/bot.py --ping post_break
  python3 src/bot.py --ping evening
  python3 src/bot.py --ping eod
"""

import asyncio
import argparse
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from claude_client import ask_pipa
from memory import append_dynamic, prune_dynamic
from prompts import PING_INSTRUCTIONS
from config import TELEGRAM_TOKEN, YOUR_CHAT_ID

# Valid ping types derived directly from prompts — no hardcoding
VALID_PINGS = [k.replace("_ping", "") for k in PING_INSTRUCTIONS.keys()]


# ── incoming message handler ──────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only respond to your own chat
    if update.effective_chat.id != YOUR_CHAT_ID:
        return

    user_text = update.message.text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Log what you said
    append_dynamic(f"[{timestamp}] user: \"{user_text.replace(chr(10), ' ').strip()}\"")

    # Ask the assistant
    reply = await ask_pipa(trigger="user_message", user_message=user_text)

    # Log the reply
    append_dynamic(f"[{timestamp}] pipa: \"{reply.replace(chr(10), ' ').strip()}\"")

    await update.message.reply_text(reply)


# ── proactive pings (called by cron) ─────────────────────────────────────────

async def send_ping(ping_type: str):
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    reply = await ask_pipa(trigger=f"{ping_type}_ping")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    append_dynamic(f"[{timestamp}] ping_sent: {ping_type}")

    async with app:
        await app.bot.send_message(chat_id=YOUR_CHAT_ID, text=reply)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ping",
        choices=VALID_PINGS,
        help=f"Send a proactive ping and exit. Options: {', '.join(VALID_PINGS)}"
    )
    args = parser.parse_args()

    # Daily prune — keep dynamic memory to last 7 days
    prune_dynamic(days=3)

    if args.ping:
        asyncio.run(send_ping(args.ping))
    else:
        # Start listener
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("PiPA is listening...")
        app.run_polling()


if __name__ == "__main__":
    main()
