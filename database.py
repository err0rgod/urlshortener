import os 
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session, select
from models import urldata
load_dotenv()

DB_PATH = os.getenv("DB_PATH")

engine = create_engine(DB_PATH)

SQLModel.metadata.create_all(engine)


def add_to_db(data : urldata):
    with Session(engine) as session:
        session.add(data)
        session.commit()


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
    
def is_long_url_exists(long_url : str):
    with Session(engine) as session:
        statement = select(urldata).where(urldata.long_url == long_url)
        results = session.exec(statement).first()
        if results is not None:
            return results.short_url
        else: 
            return None