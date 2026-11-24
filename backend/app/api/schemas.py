import uuid

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    display_name: str
    is_admin: bool
    is_active: bool


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class SessionOut(BaseModel):
    user: UserOut
    csrf_token: str


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=EMAIL_PATTERN)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    is_admin: bool = False


class UserActive(BaseModel):
    is_active: bool
