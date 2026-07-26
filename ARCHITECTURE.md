# Architecture

This file documents the architecture and conventions of this repository, for anyone working on the code.

## What this is

PiPA is a personal Telegram assistant bot template intended to run on a Raspberry Pi (or any always-on machine). It's a single-user PA/behavioural-coach bot: two-way chat via Telegram, backed by the Claude API, with read/write access to the owner's Google Calendar, and a two-tier memory system (static goals/rules + a rolling dynamic log). It also fires proactive "pings" on a cron schedule tied to the owner's daily routine (morning check-in, pre-focus-block nudge, post-break ignition, evening wind-down, EOD ritual, etc). All of the persona, schedule, and routine content is meant to be filled in per-deployment — see [README.md](README.md).

Application code lives under `src/`; one-off tooling is in `scripts/`, the systemd unit in `systemd/`, secrets in `credentials/`, and the setup guide in `docs/`.

## Running it

There is no build step, package manifest, or test suite — this is a small, directly-run Python script set. `src/`'s modules import each other as plain siblings (`from claude_client import ask_pipa`, etc.) — no `__init__.py` or packaging, Python just adds the invoked script's own directory to `sys.path`.

```bash
# Install deps (no requirements.txt exists; these are the packages used)
pip3 install anthropic python-telegram-bot google-auth google-auth-oauthlib google-api-python-client --break-system-packages

# One-time Google Calendar OAuth (interactive — opens a URL, prompts for a code)
python3 scripts/oauth_setup.py

# Start the long-running Telegram listener
python3 src/bot.py

# Fire a single proactive ping and exit (used by cron; see below for valid names)
python3 src/bot.py --ping morning
python3 src/bot.py --ping midday
python3 src/bot.py --ping pre_focus
python3 src/bot.py --ping post_break
python3 src/bot.py --ping evening
python3 src/bot.py --ping eod
```

Valid `--ping` values are derived at runtime from the keys of `PING_INSTRUCTIONS` in [prompts.py](src/prompts.py) (stripped of the `_ping` suffix) — don't hardcode a ping list elsewhere; add a new ping by adding a `<name>_ping` entry there and `bot.py` picks it up automatically.

Required environment variables (see [config.py](src/config.py)): `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`; optional `BOT_NAME` (default `PiPA`) and `TIMEZONE` (IANA name, default `UTC`). In production these are set via `EnvironmentFile=credentials/.env` in [pipa.service](systemd/pipa.service) (systemd unit); for manual runs, `cp credentials/.env.example credentials/.env`, fill it in, and export/load it. There is no test framework, linter, or CI configured in this repo.

## Architecture

**Request flow (`bot.py` → `claude_client.py`):**
- `bot.py` is the Telegram entry point. It has two triggers: incoming text messages (`handle_message`) and cron-fired proactive pings (`send_ping`). Both funnel into `ask_pipa(trigger, user_message)` in [claude_client.py](src/claude_client.py).
- `ask_pipa` builds a single context string via `build_context()` — current local date/time (per the `TIMEZONE` config), today's live calendar (fetched fresh every call, never cached), static memory, dynamic memory, and either the user's message or the ping's instruction text from `prompts.py` — then runs a tool-use loop against the Claude API (model `claude-haiku-4-5-20251001`, capped at 10 iterations) until it gets a final text reply.
- The bot only ever responds in the single chat identified by `YOUR_CHAT_ID`; every other chat is silently ignored. This is intentionally single-tenant, not a general-purpose bot.

**Calendar as Claude tools:**
- `create_event`, `update_event`, `delete_event` are plain Python functions in `claude_client.py`, exposed to Claude via the `TOOLS` schema list and dispatched through `dispatch_tool()`. All calendar ops go through `get_calendar_service()`, which loads `token.json`, refreshes it if expired or expiring within 5 minutes, and writes the refreshed token straight back to disk.
- `update_event` is known to have silent failure modes — both the tool description and `SYSTEM_PROMPT` steer Claude toward delete+recreate for time/title changes, reserving `update_event` for description-only edits. Preserve this steering if touching prompts or tool descriptions.
- Auth failures raise `RuntimeError` from `get_calendar_service()`, which callers convert into `FAILED (auth): ...` strings rather than exceptions — the system prompt explicitly instructs Claude to check for a `SUCCESS`/`FAILED` prefix before ever telling the user an action succeeded. Keep that contract (SUCCESS/FAILED string prefixes) if adding new tools.

**Memory system (`memory.py`):**
- Two files under `memory/`: `static_memory.md` (goals, schedule anchors, known failure modes — hand-edited by the owner, ships as a placeholder template) and `dynamic_memory.md` (append-only timestamped log of user messages, bot replies, and ping-sent events; gitignored since it accumulates real personal state at runtime).
- Every dynamic memory line must start with `[YYYY-MM-DD HH:MM]` — `prune_dynamic()` parses that exact prefix (`line[1:17]`) to decide what to keep, and `bot.py` calls `prune_dynamic(days=3)` on every startup. Malformed lines are kept rather than dropped, so a broken timestamp format silently defeats pruning rather than crashing it.
- Both memory files are dumped in full into every single Claude API call via `build_context()` — there's no summarization or retrieval step, so keep this in mind if `dynamic_memory.md` is ever allowed to grow past the 3-day prune window.

**Prompts (`prompts.py`):**
- `SYSTEM_PROMPT` encodes the bot's persona and behavioural rules only (never lecture, never confirm a FAILED calendar op as done, max 5-6 lines per message, etc) — it deliberately does NOT hardcode facts about the user (name, schedule, goals); those come from `static_memory.md` at request time, avoiding duplication. `PING_INSTRUCTIONS` is a dict of per-ping instructions keyed by `<name>_ping`, each a template for a generic daily transition point (morning, midday, pre-focus-block, post-break, evening, EOD). Both `SYSTEM_PROMPT` and the ping templates interpolate `BOT_NAME` from `config.py`. Changes to the deployment owner's routine/goals should go in `static_memory.md`, not here; `prompts.py` is for behavioural instructions to Claude, not facts about the user's current state.

## Secrets in this repo

`credentials/.env`, `credentials/credentials.json`, and `credentials/token.json` hold live secrets (Telegram/Anthropic tokens, Google OAuth client secret, and a refreshable Google OAuth token, respectively) once configured. They are gitignored (see `.gitignore`) and must never be committed; `credentials/.env.example` and `credentials/credentials.json.example` are the templates to copy from. Never print, log, or transmit the contents of the real files.
