from sqlmodel import SQLModel, Field
from datetime import datetime, UTC


class urldata(SQLModel, table = True):
    short_url : str = Field(primary_key=True, nullable=False, max_length=20)
    long_url : str
    created_at : datetime = Field(default_factory=lambda:datetime.now(UTC))
    click_count: int = Field(default=0)