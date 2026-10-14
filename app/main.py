import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import healthcheck, init_database
from app.routers import calendar, intent, reminders, todos, vapi_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("voiceassistant")

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = await init_database()
    logger.info("Voice Assistant ready -> http://127.0.0.1:8000 (db: %s)", url)
    yield


app = FastAPI(title="Voice Assistant API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(todos.router)
app.include_router(reminders.router)
app.include_router(calendar.router)
app.include_router(vapi_tools.router)
app.include_router(intent.router)


@app.get("/health")
async def health_check():
    return await healthcheck()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/favicon.svg")


app.mount("/", StaticFiles(directory=BASE_DIR / "web", html=True), name="web")
