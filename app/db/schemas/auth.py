from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int
    user_name: str
    email: str



class TokenData(BaseModel):
    username: str | None = None


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: float | None = None
