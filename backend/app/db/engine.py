# backend/app/db/engine.py
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/memsearch",
)

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)
