from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_calendar_entry, delete_calendar_entry, get_calendar_entries
from app.database import get_db
from app.schemas import CalendarEntryCreate, CalendarEntryResponse

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("", response_model=list[CalendarEntryResponse])
async def list_calendar_entries(db: AsyncSession = Depends(get_db)):
    return await get_calendar_entries(db)


@router.post("", response_model=CalendarEntryResponse, status_code=201)
async def add_calendar_entry(entry: CalendarEntryCreate, db: AsyncSession = Depends(get_db)):
    return await create_calendar_entry(
        db,
        title=entry.title,
        start_time=entry.start_time,
        end_time=entry.end_time,
        description=entry.description,
    )


@router.delete("/{entry_id}", status_code=204)
async def remove_calendar_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_calendar_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Calendar entry not found")
