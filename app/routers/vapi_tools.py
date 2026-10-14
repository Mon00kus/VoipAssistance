from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    complete_todo as complete_todo_crud,
    create_calendar_entry,
    create_reminder,
    create_todo,
    delete_calendar_entry,
    delete_reminder,
    delete_todo,
    get_calendar_entries,
    get_reminders,
    get_todos,
)
from app.database import get_db
from app.schemas import VapiWebhookPayload

router = APIRouter(prefix="/webhooks/vapi", tags=["vapi"])


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@router.post("/create-todo")
async def handle_create_todo(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    title = payload.parameters.get("title", "").strip()
    if not title:
        return {"result": "I need a title for the todo. What would you like to add?"}
    description = payload.parameters.get("description")
    todo = await create_todo(db, title=title, description=description)
    return {"result": f"Todo '{todo.title}' has been created."}


@router.post("/list-todos")
async def handle_list_todos(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    include_completed = payload.parameters.get("include_completed", True)
    todos = await get_todos(db, include_completed=include_completed)
    if not todos:
        return {"result": "You have no to-dos."}
    items = [f"{t.title} ({'completed' if t.completed else 'pending'})" for t in todos]
    return {"result": f"You have {len(todos)} to-dos: " + "; ".join(items)}


@router.post("/complete-todo")
async def handle_complete_todo(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    todo_id = payload.parameters.get("todo_id")
    title = payload.parameters.get("title", "").strip()
    if not todo_id and title:
        todos = await get_todos(db)
        matches = [t for t in todos if title.lower() in t.title.lower()]
        if matches:
            todo_id = matches[0].id
    if not todo_id:
        return {"result": "I couldn't find that to-do. Please specify the title or ID."}
    todo = await complete_todo_crud(db, int(todo_id))
    if not todo:
        return {"result": "That to-do was not found."}
    return {"result": f"Todo '{todo.title}' marked as completed."}


@router.post("/delete-todo")
async def handle_delete_todo(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    todo_id = payload.parameters.get("todo_id")
    title = payload.parameters.get("title", "").strip()
    if not todo_id and title:
        todos = await get_todos(db)
        matches = [t for t in todos if title.lower() in t.title.lower()]
        if matches:
            todo_id = matches[0].id
    if not todo_id:
        return {"result": "I couldn't find that to-do. Please specify the title or ID."}
    deleted = await delete_todo(db, int(todo_id))
    if not deleted:
        return {"result": "That to-do was not found."}
    return {"result": "The to-do has been deleted."}


@router.post("/add-reminder")
async def handle_add_reminder(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    title = payload.parameters.get("title", "").strip()
    if not title:
        return {"result": "I need a title for the reminder."}
    time_str = payload.parameters.get("time")
    reminder_time = _parse_datetime(time_str)
    if not reminder_time:
        reminder_time = datetime.now() + timedelta(hours=1)
    reminder = await create_reminder(db, title=title, reminder_time=reminder_time)
    return {"result": f"Reminder '{reminder.title}' set for {reminder.reminder_time.strftime('%I:%M %p')}."}


@router.post("/list-reminders")
async def handle_list_reminders(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    reminders = await get_reminders(db)
    if not reminders:
        return {"result": "You have no reminders."}
    items = [f"{r.title} at {r.reminder_time.strftime('%I:%M %p')}" for r in reminders]
    return {"result": f"You have {len(reminders)} reminders: " + "; ".join(items)}


@router.post("/add-calendar-entry")
async def handle_add_calendar_entry(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    title = payload.parameters.get("title", "").strip()
    if not title:
        return {"result": "I need a title for the calendar entry."}
    start_str = payload.parameters.get("start_time")
    end_str = payload.parameters.get("end_time")
    start_time = _parse_datetime(start_str)
    if not start_time:
        start_time = datetime.now() + timedelta(hours=1)
    end_time = _parse_datetime(end_str)
    description = payload.parameters.get("description")
    entry = await create_calendar_entry(
        db, title=title, start_time=start_time, end_time=end_time, description=description
    )
    return {"result": f"Calendar entry '{entry.title}' added for {entry.start_time.strftime('%I:%M %p')}."}


@router.post("/list-calendar-entries")
async def handle_list_calendar_entries(payload: VapiWebhookPayload, db: AsyncSession = Depends(get_db)):
    entries = await get_calendar_entries(db)
    if not entries:
        return {"result": "You have no calendar entries."}
    items = [f"{e.title} at {e.start_time.strftime('%I:%M %p')}" for e in entries]
    return {"result": f"You have {len(entries)} calendar entries: " + "; ".join(items)}
