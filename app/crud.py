from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CalendarEntry, Reminder, Todo


async def get_todos(db: AsyncSession, include_completed: bool = True) -> list[Todo]:
    stmt = select(Todo).order_by(Todo.created_at.desc())
    if not include_completed:
        stmt = stmt.where(Todo.completed.is_(False))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_todo_by_id(db: AsyncSession, todo_id: int) -> Todo | None:
    return await db.get(Todo, todo_id)


async def search_todos(db: AsyncSession, query: str) -> list[Todo]:
    stmt = select(Todo).where(Todo.title.ilike(f"%{query}%")).order_by(Todo.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_todo(db: AsyncSession, title: str, description: str | None = None) -> Todo:
    todo = Todo(title=title, description=description)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


async def update_todo(
    db: AsyncSession,
    todo_id: int,
    title: str | None = None,
    description: str | None = None,
    completed: bool | None = None,
) -> Todo | None:
    todo = await db.get(Todo, todo_id)
    if not todo:
        return None
    if title is not None:
        todo.title = title
    if description is not None:
        todo.description = description
    if completed is not None:
        todo.completed = completed
    await db.commit()
    await db.refresh(todo)
    return todo


async def complete_todo(db: AsyncSession, todo_id: int) -> Todo | None:
    return await update_todo(db, todo_id=todo_id, completed=True)


async def delete_todo(db: AsyncSession, todo_id: int) -> bool:
    todo = await db.get(Todo, todo_id)
    if not todo:
        return False
    await db.delete(todo)
    await db.commit()
    return True


async def get_reminders(db: AsyncSession) -> list[Reminder]:
    stmt = select(Reminder).order_by(Reminder.reminder_time.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_reminder(
    db: AsyncSession, title: str, reminder_time: datetime, todo_id: int | None = None
) -> Reminder:
    reminder = Reminder(title=title, reminder_time=reminder_time, todo_id=todo_id)
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def delete_reminder(db: AsyncSession, reminder_id: int) -> bool:
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        return False
    await db.delete(reminder)
    await db.commit()
    return True


async def get_calendar_entries(db: AsyncSession) -> list[CalendarEntry]:
    stmt = select(CalendarEntry).order_by(CalendarEntry.start_time.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_calendar_entry(
    db: AsyncSession,
    title: str,
    start_time: datetime,
    end_time: datetime | None = None,
    description: str | None = None,
) -> CalendarEntry:
    entry = CalendarEntry(title=title, start_time=start_time, end_time=end_time, description=description)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def delete_calendar_entry(db: AsyncSession, entry_id: int) -> bool:
    entry = await db.get(CalendarEntry, entry_id)
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()
    return True
