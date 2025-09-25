from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# PostgreSQL bağlantı bilgileri
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "12345"
POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = "5432"
POSTGRES_DB = "restaurant_db"

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
