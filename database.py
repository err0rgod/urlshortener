import os 
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session
from models import urldata
load_dotenv()

DB_PATH = os.getenv("DB_PATH")

engine = create_engine(DB_PATH,echo=True)

SQLModel.metadata.create_all(engine)


def add_to_db(data : urldata):
    with Session(engine) as session:
        session.add(data)
        session.commit()