import os 
from dotenv import load_dotenv
from sqlmodel import create_engine,SQLModel, Session, select
from typing import Optional
from models import urldata, User
from datetime import datetime, UTC


load_dotenv()

DB_PATH = os.getenv("DB_PATH")

engine = create_engine(DB_PATH)

def init_db():
    SQLModel.metadata.create_all(engine)


def add_to_db(data : urldata):
    with Session(engine) as session:
        session.add(data)
        session.commit()

def is_alias_exists(custom_alias : str) -> bool:
    with Session(engine) as session:
        statement = select(urldata).where(urldata.short_url == custom_alias)
        url = session.exec(statement).first()
        if url:
            return True
        return False

def get_long_url(short_url) -> str:
    with Session(engine) as session:
        statement = select(urldata).where(urldata.short_url == short_url)
        url = session.exec(statement).first()
        if url is None:
            return None
        if url.is_banned:
            return "BANNED"
        url.click_count+=1
        session.add(url)
        session.commit()
        session.refresh(url)
        return url.long_url

def mark_url_banned(short_url: str):
    with Session(engine) as session:
        statement = select(urldata).where(urldata.short_url == short_url)
        url = session.exec(statement).first()
        if url:
            url.is_banned = True
            session.add(url)
            session.commit()
    
def is_long_url_exists(long_url : str, user_id: Optional[int] = None):
    with Session(engine) as session:
        statement = select(urldata).where(urldata.long_url == long_url)
        results = session.exec(statement).first()
        if results is not None:
            if user_id and results.user_id is None:
                results.user_id = user_id
                session.add(results)
                session.commit()
            return results.short_url
        else: 
            return None
        



def get_user_by_email(email : str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(email == User.email)
        return session.exec(statement).first()
    

def create_user(email : str, full_name : str, oauth_provider : str, oauth_id : str)->User:
    with Session(engine) as session:
        user = User(
            email=email,
            full_name=full_name,
            oauth_id=oauth_id,
            oauth_provider=oauth_provider,
            created_at=datetime.now(UTC)
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user