import re
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    complete_todo as complete_todo_crud,
    create_calendar_entry,
    create_reminder,
    create_todo,
    delete_reminder,
    delete_todo,
    get_calendar_entries,
    get_reminders,
    get_todos,
)

TODO_WORDS = ("todo", "to-do", "to do", "task")
REMINDER_WORDS = ("reminder", "remind")
CALENDAR_WORDS = ("calendar", "schedule", "appointment", "event", "meeting", "call with")
ADD_WORDS = ("add", "create", "new", "make", "put")
SCHEDULE_VERBS = ("schedule", "book", "arrange")
COMPLETE_WORDS = ("complete", "finish", "done", "mark")
DELETE_WORDS = ("delete", "remove", "erase", "cancel")
LIST_WORDS = ("list", "show", "what", "my", "read", "give me")


def _parse_time(text: str) -> datetime | None:
    text = text.lower().strip()
    now = datetime.now()

    if "tomorrow" in text:
        base = now + timedelta(days=1)
    elif "today" in text or "tonight" in text:
        base = now
    else:
        base = now

    if "morning" in text:
        return base.replace(hour=9, minute=0, second=0, microsecond=0)
    if "afternoon" in text:
        return base.replace(hour=14, minute=0, second=0, microsecond=0)
    if "evening" in text:
        return base.replace(hour=18, minute=0, second=0, microsecond=0)
    if "tonight" in text:
        return base.replace(hour=20, minute=0, second=0, microsecond=0)

    time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = time_match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return None


def _split_time(text: str) -> tuple[str, datetime | None]:
    """Strip a trailing time expression off the utterance, returning the remaining text."""
    match = re.search(r"\s+(?:at|for|on)\s+(.+)$", text, re.IGNORECASE)
    if not match:
        return text.strip(), None
    remainder = text[: match.start()].strip()
    parsed = _parse_time(match.group(1))
    if parsed is None:
        return text.strip(), None
    return remainder, parsed


def _clean_title(text: str, prefix_pattern: str, suffix_pattern: str = r"") -> str:
    title = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE)
    if suffix_pattern:
        title = re.sub(suffix_pattern, "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"\s+(?:today|tomorrow|tonight|this\s+(?:morning|afternoon|evening)|"
        r"next\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday))$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    return title.strip(" ,:-")


def _find_todo(todos: list, needle: str) -> object | None:
    needle = needle.lower().strip()
    if not needle:
        return None
    for todo in todos:
        if todo.title.lower() == needle:
            return todo
    for todo in todos:
        if needle in todo.title.lower():
            return todo
    tokens = [t for t in re.split(r"\W+", needle) if len(t) > 2]
    if tokens:
        for todo in todos:
            if all(t in todo.title.lower() for t in tokens):
                return todo
    return None


def _format_time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


async def _handle_add_todo(text: str, db: AsyncSession) -> dict:
    title = _clean_title(
        text,
        r"^(?:please\s+)?(?:add|create|new|make|put)\s+(?:an?\s+|the\s+)?(?:todo|task|to-do|item)?\s*(?:to\s+)?",
        r"\s+(?:to|in|on)\s+(?:my\s+)?(?:todo|to-do|to do|task)\s*(?:list)?$",
    )
    if not title:
        return {"reply": "What would you like to add to your to-do list?", "action": "clarify"}
    todo = await create_todo(db, title=title)
    return {
        "reply": f"I've added '{todo.title}' to your to-do list.",
        "action": "create_todo",
        "data": {"id": todo.id},
    }


async def _handle_complete_todo(text: str, db: AsyncSession) -> dict:
    todos = await get_todos(db, include_completed=False)
    title = _clean_title(
        text,
        r"^(?:please\s+)?(?:complete|finish|mark|check off|cross off)\s+(?:off\s+)?(?:the\s+)?(?:todo|task|to-do|item)?\s*(?:as\s+)?",
        r"\s+as\s+(?:done|complete|completed|finished)$",
    )
    match = _find_todo(todos, title)
    if match is None:
        match = _find_todo(todos, _clean_title(text, r"^(?:please\s+)?(?:i(?:'ve)?\s+)?(?:done|finished)\s+(?:with\s+)?"))
    if match is not None:
        updated = await complete_todo_crud(db, match.id)
        return {
            "reply": f"Great, I've marked '{updated.title}' as completed.",
            "action": "complete_todo",
            "data": {"id": updated.id},
        }
    if todos:
        listing = ", ".join(t.title for t in todos[:5])
        return {
            "reply": f"Which to-do should I complete? You have: {listing}.",
            "action": "clarify",
        }
    return {"reply": "You have no pending to-dos to complete.", "action": "none"}


async def _handle_delete_todo(text: str, db: AsyncSession) -> dict:
    todos = await get_todos(db)
    title = _clean_title(
        text,
        r"^(?:please\s+)?(?:delete|remove|erase|cancel)\s+(?:the\s+)?(?:todo|task|to-do|item)?\s*",
    )
    match = _find_todo(todos, title)
    if match is not None:
        await delete_todo(db, match.id)
        return {
            "reply": f"I've deleted '{match.title}' from your to-do list.",
            "action": "delete_todo",
            "data": {"id": match.id},
        }
    if todos:
        listing = ", ".join(t.title for t in todos[:5])
        return {
            "reply": f"Which to-do should I delete? You have: {listing}.",
            "action": "clarify",
        }
    return {"reply": "You have no to-dos to delete.", "action": "none"}


async def _handle_list_todos(db: AsyncSession, include_completed: bool = True) -> dict:
    todos = await get_todos(db, include_completed=include_completed)
    if not todos:
        return {
            "reply": "You have no pending to-dos." if not include_completed else "You have no to-dos.",
            "action": "list_todos",
            "data": {"items": []},
        }
    items = [
        f"{t.title} ({'completed' if t.completed else 'pending'})" if include_completed else t.title
        for t in todos
    ]
    return {
        "reply": f"You have {len(todos)} to-dos: {', '.join(items)}.",
        "action": "list_todos",
        "data": {"items": [{"id": t.id, "title": t.title, "completed": t.completed} for t in todos]},
    }


async def _handle_add_reminder(text: str, db: AsyncSession) -> dict:
    remainder, parsed_time = _split_time(text)
    reminder_time = parsed_time or (datetime.now() + timedelta(hours=1))
    title = _clean_title(
        remainder,
        r"^(?:please\s+)?(?:add|create|set|new)\s+(?:an?\s+|the\s+)?reminder\s+(?:to\s+|for\s+)?",
    )
    title = _clean_title(title, r"^remind\s+me\s+(?:to\s+|about\s+|that\s+)?")
    title = _clean_title(title, r"", r"\s+(?:to|in|on)\s+(?:my\s+)?reminder\s*list$")
    if not title:
        return {"reply": "What would you like to be reminded about?", "action": "clarify"}
    reminder = await create_reminder(db, title=title, reminder_time=reminder_time)
    return {
        "reply": f"Reminder set for '{reminder.title}' at {_format_time(reminder.reminder_time)}.",
        "action": "add_reminder",
        "data": {"id": reminder.id},
    }


async def _handle_list_reminders(db: AsyncSession) -> dict:
    reminders = await get_reminders(db)
    if not reminders:
        return {"reply": "You have no reminders.", "action": "list_reminders", "data": {"items": []}}
    items = [f"{r.title} at {_format_time(r.reminder_time)}" for r in reminders]
    return {
        "reply": f"You have {len(reminders)} reminders: {', '.join(items)}.",
        "action": "list_reminders",
        "data": {"items": [{"id": r.id, "title": r.title} for r in reminders]},
    }


async def _handle_add_calendar(text: str, db: AsyncSession) -> dict:
    remainder, parsed_time = _split_time(text)
    start_time = parsed_time or (datetime.now() + timedelta(hours=1))
    title = _clean_title(
        remainder,
        r"^(?:please\s+)?(?:add|create|schedule|new|book)\s+(?:an?\s+|the\s+)?"
        r"(?:calendar\s+)?(?:entry|event|appointment|meeting)?\s*[:\-]?\s*",
    )
    title = _clean_title(title, r"", r"\s+(?:to|in|on)\s+(?:my\s+)?calendar(?:\s+entry)?$")
    if not title:
        for noun in ("meeting", "appointment", "event", "calendar entry"):
            if noun in remainder.lower():
                title = noun
                break
    if not title:
        return {"reply": "What would you like to add to your calendar?", "action": "clarify"}
    entry = await create_calendar_entry(db, title=title, start_time=start_time)
    return {
        "reply": f"Calendar entry '{entry.title}' added for {_format_time(entry.start_time)}.",
        "action": "add_calendar_entry",
        "data": {"id": entry.id},
    }


async def _handle_list_calendar(db: AsyncSession) -> dict:
    entries = await get_calendar_entries(db)
    if not entries:
        return {
            "reply": "You have no calendar entries.",
            "action": "list_calendar",
            "data": {"items": []},
        }
    items = [f"{e.title} at {_format_time(e.start_time)}" for e in entries]
    return {
        "reply": f"You have {len(entries)} calendar entries: {', '.join(items)}.",
        "action": "list_calendar",
        "data": {"items": [{"id": e.id, "title": e.title} for e in entries]},
    }


async def parse_intent(text: str, db: AsyncSession) -> dict:
    lowered = text.lower().strip()
    wants_list = any(kw in lowered for kw in LIST_WORDS)
    imperative_schedule = any(lowered.startswith(f"{v} ") or lowered == v for v in SCHEDULE_VERBS)
    wants_add = any(kw in lowered for kw in ADD_WORDS) or imperative_schedule or lowered.startswith("remind")
    wants_complete = any(kw in lowered for kw in COMPLETE_WORDS)
    wants_delete = any(kw in lowered for kw in DELETE_WORDS)

    mentions_todo = any(w in lowered for w in TODO_WORDS)
    mentions_reminder = any(w in lowered for w in REMINDER_WORDS)
    mentions_calendar = any(w in lowered for w in CALENDAR_WORDS)

    # Reminders take priority: "remind me to X" is a reminder, not a to-do.
    if mentions_reminder:
        if wants_add:
            return await _handle_add_reminder(text, db)
        if wants_delete:
            reminders = await get_reminders(db)
            title = _clean_title(text, r"^(?:please\s+)?(?:delete|remove|cancel)\s+(?:the\s+)?reminder\s*")
            match = next((r for r in reminders if title.lower() in r.title.lower()), None)
            if match is not None:
                await delete_reminder(db, match.id)
                return {
                    "reply": f"I've deleted the reminder '{match.title}'.",
                    "action": "delete_reminder",
                    "data": {"id": match.id},
                }
            return {"reply": "I couldn't find that reminder.", "action": "clarify"}
        if wants_list or not wants_add:
            return await _handle_list_reminders(db)

    if mentions_calendar:
        if wants_add:
            return await _handle_add_calendar(text, db)
        if wants_list or not (wants_complete or wants_delete):
            return await _handle_list_calendar(db)

    if mentions_todo:
        if wants_add:
            return await _handle_add_todo(text, db)
        if wants_complete:
            return await _handle_complete_todo(text, db)
        if wants_delete:
            return await _handle_delete_todo(text, db)
        if wants_list:
            return await _handle_list_todos(db, include_completed=False)

    # Fallbacks: bare commands with no explicit entity keyword.
    if wants_add and not lowered.startswith(("what", "who")):
        return await _handle_add_todo(text, db)
    if wants_complete:
        return await _handle_complete_todo(text, db)
    if wants_delete:
        return await _handle_delete_todo(text, db)
    if wants_list:
        return await _handle_list_todos(db, include_completed=False)

    return {
        "reply": (
            "I'm not sure what you'd like to do. You can ask me to add, list, complete, or delete "
            "to-dos, set reminders, or schedule calendar entries."
        ),
        "action": "unknown",
    }
