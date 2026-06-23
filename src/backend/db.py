import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.environ.get("DATABASE_URL", "")

engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


class Base(DeclarativeBase):
    pass


def get_db():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not set — add it to src/backend/.env")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
