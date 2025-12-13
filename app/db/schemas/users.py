from pydantic import BaseModel, constr, EmailStr, Field
from datetime import date
from typing import Optional



class UsersBase(BaseModel):
    email: EmailStr
    name: str
    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None

    class Config:
        orm_mode = True

class UsersCreate(UsersBase):
    password: str = Field(alias="password")

class Users(UsersBase):
    id: int
    creation_date: date
