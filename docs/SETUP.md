# Setup

Full walkthrough for deploying PiPA on a Raspberry Pi (or any always-on Linux box).

## 1. Install dependencies

```bash
pip3 install anthropic python-telegram-bot google-auth google-auth-oauthlib google-api-python-client --break-system-packages
```

## 2. Configure secrets

```bash
cp credentials/.env.example credentials/.env
```

Edit `credentials/.env`: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`, `BOT_NAME`, `TIMEZONE`.

## 3. Set up Google Calendar OAuth

- In Google Cloud Console, create an OAuth client (Desktop app), enable the Calendar API, and download the client secret as `credentials/credentials.json` (see `credentials/credentials.json.example` for the expected shape).
- Then run once, interactively:

```bash
python3 scripts/oauth_setup.py
```

This produces `credentials/token.json`, which is auto-refreshed from then on.

## 4. Run as a systemd service

Copy `systemd/pipa.service` to `/etc/systemd/system/pipa.service`, filling in your username/path, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pipa
sudo systemctl start pipa
sudo systemctl status pipa
```

## 5. Add cron jobs for proactive pings

Run `crontab -e` and add lines like these, matched to your own schedule and to the ping keys in `src/prompts.py`'s `PING_INSTRUCTIONS` (rename/add/remove pings there freely):

```
# Morning ping
30 8 * * * cd /home/YOUR_USERNAME/pipa && python3 src/bot.py --ping morning

# Midday ping
30 10 * * * cd /home/YOUR_USERNAME/pipa && python3 src/bot.py --ping midday

# Pre-focus-block ping (weekdays only, adjust day range as needed)
45 15 * * 1-5 cd /home/YOUR_USERNAME/pipa && python3 src/bot.py --ping pre_focus

# Post-break ping
30 19 * * * cd /home/YOUR_USERNAME/pipa && python3 src/bot.py --ping post_break

# Evening ping
45 20 * * * cd /home/YOUR_USERNAME/pipa && python3 src/bot.py --ping evening

# End-of-day ping
20 23 * * * cd /home/YOUR_USERNAME/pipa && python3 src/bot.py --ping eod
```
