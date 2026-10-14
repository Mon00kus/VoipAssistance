from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import IntentRequest, IntentResponse
from app.services.intent_parser import parse_intent

router = APIRouter(prefix="/api", tags=["intent"])


@router.post("/intent", response_model=IntentResponse)
async def process_intent(request: IntentRequest, db: AsyncSession = Depends(get_db)):
    result = await parse_intent(request.text, db)
    return IntentResponse(**result)
