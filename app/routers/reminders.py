from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_reminder, delete_reminder, get_reminders
from app.database import get_db
from app.schemas import ReminderCreate, ReminderResponse

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(db: AsyncSession = Depends(get_db)):
    return await get_reminders(db)


@router.post("", response_model=ReminderResponse, status_code=201)
async def add_reminder(reminder: ReminderCreate, db: AsyncSession = Depends(get_db)):
    return await create_reminder(
        db,
        title=reminder.title,
        reminder_time=reminder.reminder_time,
        todo_id=reminder.todo_id,
    )


@router.delete("/{reminder_id}", status_code=204)
async def remove_reminder(reminder_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_reminder(db, reminder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Reminder not found")
