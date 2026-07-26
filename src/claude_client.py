"""
claude_client.py
Builds context and calls Claude API with calendar read + write tools.
- AsyncAnthropic client
- Fetches calendar events via Google SDK
- Exposes create_event, update_event, delete_event as Claude tools
- Handles tool call loop with verification
"""

import anthropic
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build

from memory import read_static, read_dynamic
from prompts import SYSTEM_PROMPT, ping_instruction
from config import ANTHROPIC_API_KEY, GOOGLE_TOKEN_PATH, TIMEZONE

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

TZ = ZoneInfo(TIMEZONE)


# ── Google Calendar service ───────────────────────────────────────────────────

def get_calendar_service():
    """
    Load credentials, refresh if expired or about to expire.
    Saves refreshed token back to disk immediately.
    Raises RuntimeError on auth failure so callers can surface it cleanly.
    """
    try:
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH)
    except Exception as e:
        raise RuntimeError(f"Cannot load token.json: {e}. Run scripts/oauth_setup.py.")

    # Refresh if expired OR if less than 5 minutes remain
    needs_refresh = creds.expired
    if not needs_refresh and creds.expiry:
        remaining = (creds.expiry.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds()
        if remaining < 300:
            needs_refresh = True

    if needs_refresh:
        if not creds.refresh_token:
            raise RuntimeError("Token expired and no refresh_token present. Run scripts/oauth_setup.py.")
        try:
            creds.refresh(Request())
            with open(GOOGLE_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        except RefreshError as e:
            raise RuntimeError(f"Token refresh failed: {e}. Run scripts/oauth_setup.py to re-authenticate.")

    return build("calendar", "v3", credentials=creds)


# ── Calendar read ─────────────────────────────────────────────────────────────

def fetch_today_events() -> str:
    try:
        service = get_calendar_service()
        now_local = datetime.now(TZ)
        start_of_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day   = now_local.replace(hour=23, minute=59, second=59, microsecond=0)

        result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = result.get("items", [])
        if not events:
            return "No events on calendar today."

        lines = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            if "T" in start:
                dt = datetime.fromisoformat(start)
                time_str = dt.astimezone(TZ).strftime("%H:%M")
            else:
                time_str = "all-day"
            lines.append(f"  {time_str}  {e.get('summary', '(no title)')}  [id:{e['id']}]")

        return "\n".join(lines)

    except RuntimeError as e:
        return f"(calendar unavailable — {e})"
    except Exception as e:
        return f"(calendar fetch failed: {e})"


# ── Calendar write tools ──────────────────────────────────────────────────────

def _local_iso(date: str, time_str: str) -> str:
    """Combine a YYYY-MM-DD date and HH:MM time into a tz-aware ISO string in TIMEZONE."""
    return datetime.fromisoformat(f"{date}T{time_str}:00").replace(tzinfo=TZ).isoformat()


def create_event(title: str, date: str, start_time: str, end_time: str, description: str = "") -> str:
    """
    Create a calendar event.
    date: YYYY-MM-DD
    start_time / end_time: HH:MM (local time, per TIMEZONE config)
    Returns confirmation with event ID, or error string.
    """
    try:
        service = get_calendar_service()
        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": _local_iso(date, start_time),
                "timeZone": TIMEZONE
            },
            "end": {
                "dateTime": _local_iso(date, end_time),
                "timeZone": TIMEZONE
            }
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        event_id = created.get("id", "unknown")
        return f"SUCCESS: Created '{title}' on {date} {start_time}–{end_time} ({TIMEZONE}). ID: {event_id}"
    except RuntimeError as e:
        return f"FAILED (auth): {e}"
    except Exception as e:
        return f"FAILED: {e}"


def delete_event(event_id: str) -> str:
    """Delete a calendar event by event_id."""
    try:
        service = get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"SUCCESS: Deleted event {event_id}."
    except RuntimeError as e:
        return f"FAILED (auth): {e}"
    except Exception as e:
        return f"FAILED: {e}"


def update_event(event_id: str, title: str = None, date: str = None,
                 start_time: str = None, end_time: str = None, description: str = None) -> str:
    """
    Update an existing calendar event.
    Preferred pattern: delete + recreate. Use this only for minor field edits.
    """
    try:
        service = get_calendar_service()
        event = service.events().get(calendarId="primary", eventId=event_id).execute()

        if title:       event["summary"] = title
        if description: event["description"] = description
        if date and start_time:
            event["start"] = {"dateTime": _local_iso(date, start_time), "timeZone": TIMEZONE}
        if date and end_time:
            event["end"]   = {"dateTime": _local_iso(date, end_time),   "timeZone": TIMEZONE}

        updated = service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
        return f"SUCCESS: Updated event '{updated['summary']}' (ID: {event_id})."
    except RuntimeError as e:
        return f"FAILED (auth): {e}"
    except Exception as e:
        return f"FAILED: {e}"


# ── Tool definitions (passed to Claude API) ───────────────────────────────────

TOOLS = [
    {
        "name": "create_event",
        "description": (
            "Create a new event on the user's Google Calendar. "
            "Returns SUCCESS with event ID on success, or FAILED with reason. "
            "Always check the return value before confirming to the user."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string", "description": "Event title"},
                "date":        {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "start_time":  {"type": "string", "description": "Start time in HH:MM (24hr, local time)"},
                "end_time":    {"type": "string", "description": "End time in HH:MM (24hr, local time)"},
                "description": {"type": "string", "description": "Optional event description"}
            },
            "required": ["title", "date", "start_time", "end_time"]
        }
    },
    {
        "name": "delete_event",
        "description": (
            "Delete a calendar event by event_id. "
            "Event IDs are shown in the TODAY'S CALENDAR block as [id:xxxxx]. "
            "Returns SUCCESS or FAILED. Check return value before confirming to the user. "
            "To reschedule an event: delete it first, then create a new one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Google Calendar event ID (from [id:xxxxx] in calendar listing)"}
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "update_event",
        "description": (
            "Update fields on an existing calendar event. "
            "WARNING: update_event has known silent failure modes. "
            "Prefer delete + create for time/title changes. "
            "Use update_event only for description-only edits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id":    {"type": "string", "description": "Google Calendar event ID"},
                "title":       {"type": "string", "description": "New title (optional)"},
                "date":        {"type": "string", "description": "New date YYYY-MM-DD (optional)"},
                "start_time":  {"type": "string", "description": "New start time HH:MM, local time (optional)"},
                "end_time":    {"type": "string", "description": "New end time HH:MM, local time (optional)"},
                "description": {"type": "string", "description": "New description (optional)"}
            },
            "required": ["event_id"]
        }
    }
]


# ── Tool dispatcher ───────────────────────────────────────────────────────────

def dispatch_tool(name: str, inputs: dict) -> str:
    if name == "create_event":
        return create_event(**inputs)
    elif name == "update_event":
        return update_event(**inputs)
    elif name == "delete_event":
        return delete_event(**inputs)
    return f"Unknown tool: {name}"


# ── Context builder ───────────────────────────────────────────────────────────

def build_context(trigger: str, user_message: str = "") -> str:
    now = datetime.now(TZ).strftime("%A, %d %b %Y — %H:%M %Z")
    context = f"""--- CONTEXT FOR THIS CONVERSATION ---

DATE & TIME: {now}
TRIGGER: {trigger}

--- TODAY'S CALENDAR ---
{fetch_today_events()}

--- STATIC MEMORY (goals and rules) ---
{read_static()}

--- DYNAMIC MEMORY (recent state, last 3 days) ---
{read_dynamic()}
"""
    if trigger == "user_message" and user_message:
        context += f"\n--- USER MESSAGE ---\n{user_message}\n"
    else:
        context += f"\n--- INSTRUCTION ---\n{ping_instruction(trigger)}\n"

    context += "\n--- END CONTEXT ---"
    return context


# ── Main API call with tool loop ──────────────────────────────────────────────

async def ask_pipa(trigger: str, user_message: str = "") -> str:
    context = build_context(trigger, user_message)
    messages = [{"role": "user", "content": context}]

    # Safety cap: never run more than 10 tool iterations
    MAX_TOOL_ITERATIONS = 10
    iterations = 0

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            # Final text response
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(text_blocks).strip()

    return "(Error: tool loop hit max iterations — check logs)"
