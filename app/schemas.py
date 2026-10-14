from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TodoBase(BaseModel):
    title: str
    description: str | None = None


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None


class TodoResponse(TodoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    completed: bool
    created_at: datetime
    updated_at: datetime


class ReminderBase(BaseModel):
    title: str
    reminder_time: datetime
    todo_id: int | None = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: str | None = None
    reminder_time: datetime | None = None


class ReminderResponse(ReminderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CalendarEntryBase(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime | None = None
    description: str | None = None


class CalendarEntryCreate(CalendarEntryBase):
    pass


class CalendarEntryUpdate(BaseModel):
    title: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    description: str | None = None


class CalendarEntryResponse(CalendarEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class VapiToolCall(BaseModel):
    name: str
    parameters: dict


class VapiWebhookPayload(BaseModel):
    toolCallId: str | None = None
    name: str | None = None
    parameters: dict = {}
    message: dict | None = None


class IntentRequest(BaseModel):
    text: str


class IntentResponse(BaseModel):
    reply: str
    action: str | None = None
    data: dict | None = None
