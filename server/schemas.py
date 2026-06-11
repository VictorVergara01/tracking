"""Request/response schemas for the API."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    name: str
    password: str
    role: str = 'client'


class StageInput(BaseModel):
    name: str
    assigned_to: str = ''
    stage_id: Optional[int] = None


class ProcessInput(BaseModel):
    name: str
    description: str = ''
    client_id: int
    due_date: Optional[date] = None  # ISO date "YYYY-MM-DD" or null
    stages: list[StageInput] = Field(default_factory=list)


class UserOut(BaseModel):
    id: int
    username: str
    name: str
    role: str
    onboarded: bool


class LoginResponse(BaseModel):
    token: str
    user: UserOut
