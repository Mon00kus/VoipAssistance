from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    create_todo,
    delete_todo,
    get_todo_by_id,
    get_todos,
    search_todos,
    update_todo,
)
from app.database import get_db
from app.schemas import TodoCreate, TodoResponse, TodoUpdate

router = APIRouter(prefix="/api/todos", tags=["todos"])


@router.get("", response_model=list[TodoResponse])
async def list_todos(
    include_completed: bool = Query(default=True),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if search:
        return await search_todos(db, search)
    return await get_todos(db, include_completed=include_completed)


@router.post("", response_model=TodoResponse, status_code=201)
async def create_new_todo(todo: TodoCreate, db: AsyncSession = Depends(get_db)):
    return await create_todo(db, title=todo.title, description=todo.description)


@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_existing_todo(todo_id: int, todo: TodoUpdate, db: AsyncSession = Depends(get_db)):
    updated = await update_todo(
        db,
        todo_id=todo_id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Todo not found")
    return updated


@router.delete("/{todo_id}", status_code=204)
async def delete_existing_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_todo(db, todo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Todo not found")
