from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str


class MeOut(BaseModel):
    username: str
