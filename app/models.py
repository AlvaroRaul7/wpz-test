from typing import Optional, List
from pydantic import BaseModel, EmailStr

class User(BaseModel):
    id: int
    firstname: str
    lastname: str
    email: Optional[EmailStr] = None
    is_external: bool

class UserCreate(BaseModel):
    firstname: str
    lastname: str
    email: Optional[EmailStr] = None
    is_external: bool

class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[EmailStr] = None
    is_external: Optional[bool] = None

class ErrorLog(BaseModel):
    userId: int
    attemptedEmail: Optional[EmailStr] = None
    error: str 