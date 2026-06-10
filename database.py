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
        url.click_count+=1
        session.add(url)
        session.commit()
        session.refresh(url)
        return url.long_url
    
def check_in_db(data : urldata):
    pass