from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, UTC


class User(SQLModel, table=True):
    __tablename__ = "users"
    id : Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True,index=True)
    full_name: str
    oauth_provider : str
    oauth_id : str
    created_at : datetime

class urldata(SQLModel, table = True):
    short_url : str = Field(primary_key=True, index=True,nullable=False, max_length=20, unique=True)
    long_url : str = Field(nullable=False, unique=True)
    created_at : datetime = Field(default_factory=lambda:datetime.now(UTC))
    click_count: int = Field(default=0)
    is_banned: bool = Field(default=False)
    user_id : Optional[int] = Field(default=None, foreign_key="users.id")