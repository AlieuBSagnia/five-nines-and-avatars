"""Pydantic schemas for request validation and response serialisation."""
from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    """Shape returned by GET /users, matching the spec exactly."""
    name: str
    email: EmailStr
    avatar_url: str


class UserCreateForm(BaseModel):
    """Validated form fields for POST /user (the avatar file itself is
    handled separately as an UploadFile since Pydantic v2 doesn't validate
    multipart file parts directly)."""
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
