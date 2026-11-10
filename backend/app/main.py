import logging
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.api import router
from app.core.config import get_settings
from app.core.request_context import reset_request_id, set_request_id
from app.db.session import dispose_engine
from app.services.ai.provider import ProviderError

logging.basicConfig(
    level=get_settings().log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await dispose_engine()


app = FastAPI(title="ESO Wizard API", version="0.2.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if _SAFE_REQUEST_ID.match(supplied) else uuid.uuid4().hex
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        reset_request_id(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(ProviderError)
async def provider_error_handler(_: Request, exc: ProviderError):
    logger.error("provider.failed error=%s", type(exc).__name__)
    return JSONResponse(status_code=502, content={"detail": "The AI service is unavailable"})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, exc: SQLAlchemyError):
    logger.error("database.failed error=%s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "The database is unavailable"})
