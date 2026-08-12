from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str


class MeOut(BaseModel):
    username: str
    role: str = "superadmin"  # WO 7.15 role; default keeps old clients working
