"""
Prima Tech Challenge — API Server.

Two business endpoints (per spec):
  GET  /users  -> list all users
  POST /user   -> create a user with an avatar image

Plus two operational endpoints used by Kubernetes probes:
  GET /healthz -> liveness (is the process up)
  GET /readyz  -> readiness (can it actually serve traffic, i.e. reach deps)
"""
import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from app import db, storage
from app.config import settings
from app.models import UserOut

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prima Tech Challenge API",
    version="1.0.0",
    description="Minimal user-management API backed by DynamoDB + S3.",
)


@app.get("/healthz", tags=["ops"])
def healthz():
    """Liveness probe: process is up and able to respond. Deliberately does
    NOT touch external dependencies, so a slow/down DB doesn't get the pod
    killed and restarted in a crash loop."""
    return {"status": "ok"}


@app.get("/readyz", tags=["ops"])
def readyz():
    """Readiness probe: verifies we can actually talk to DynamoDB, so
    Kubernetes stops routing traffic to this pod if the dependency is down,
    without restarting the container."""
    try:
        db.list_users()
        return {"status": "ready"}
    except db.DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@app.get("/users", response_model=list[UserOut], tags=["users"])
def get_users():
    """Retrieve a list of all users."""
    try:
        items = db.list_users()
    except db.DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return [UserOut(**item) for item in items]


@app.post("/user", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["users"])
async def create_user(
    name: str = Form(..., min_length=1, max_length=100),
    email: str = Form(...),
    avatar: UploadFile = File(...),
):
    """Create a new user, uploading the provided image as their avatar."""
    # Validate email format explicitly (Form() doesn't run Pydantic's EmailStr
    # validation for us, since these are plain multipart form fields).
    from email.utils import parseaddr
    if "@" not in email or parseaddr(email)[1] != email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email address")

    if avatar.content_type not in settings.ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported avatar content type: {avatar.content_type}. "
                   f"Allowed: {', '.join(settings.ALLOWED_AVATAR_CONTENT_TYPES)}",
        )

    file_bytes = await avatar.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avatar file is empty")
    if len(file_bytes) > settings.MAX_AVATAR_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Avatar exceeds max size of {settings.MAX_AVATAR_SIZE_BYTES} bytes",
        )

    try:
        avatar_url = storage.upload_avatar(file_bytes, avatar.content_type, avatar.filename or "avatar")
    except storage.StorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    try:
        created = db.create_user(name=name, email=email, avatar_url=avatar_url)
    except db.DuplicateUserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except db.DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return UserOut(**created)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Catch-all so unexpected errors never leak stack traces to clients."""
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
