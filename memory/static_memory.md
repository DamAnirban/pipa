<!--
static_memory.md
Hand-edited by you. This is the model's persistent knowledge of your goals,
schedule, rules, and known failure modes — it's injected into every
conversation (see read_static() / build_context()). Update it whenever your
goals or routine change; there's no fixed cadence, but a weekly pass works well.

Replace the placeholder sections below with your own. Delete this comment block
once you've filled it in.
-->

## Goals
- <e.g. "Ship side project X by <date>">
- <e.g. "Sleep 8+ hrs/night consistently">
- <e.g. "Exercise 4x/week">

## Schedule anchors
- <time range>: <block, e.g. "work">
- <time range>: <block, e.g. "focus/study block">
- <time range>: <block, e.g. "break/rest">
- <time>: <e.g. "dinner anchor">
- <time>: <e.g. "end-of-day ritual">
- Sleep target: <bedtime> – <wake time>

## Rules
- <e.g. "After a break, top priority first — admin/low-value work second">
- <e.g. "Skip a habit only for a genuine reason, not just low motivation">

## Known failure modes
- <patterns you've noticed that derail your day — the more specific, the more useful this is to the model>

## Bot
- Telegram bot, always on via systemd
- Reads Google Calendar (live) and dynamic memory on every call
- Can create, delete, and update calendar events via Google Calendar API
- Rolling dynamic memory: 3-day window

## Ping schedule
<!-- Match this to whatever cron schedule you set up (see docs/SETUP.md) -->
- <time> — morning (day setup, energy check)
- <time> — midday (focus check, drift catch)
- <time> — pre-focus (reminder before a scheduled focus/study block)
- <time> — post-break (re-engagement after nap/gym/walk/etc.)
- <time> — evening (wind-down, honest read of the day)
- <time> — eod (end-of-day ritual trigger)
