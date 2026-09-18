"""Azure SQL / SQL Server database configuration."""

from __future__ import annotations

import os
from contextlib import contextmanager
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def build_connection_url() -> str:
    """Build an encrypted pyodbc connection URL for Azure SQL."""

    driver = os.getenv("DATABASE_DRIVER", "ODBC Driver 18 for SQL Server")
    server = _required("DATABASE_SERVER")
    database = _required("DATABASE_NAME")
    username = _required("DATABASE_USERNAME")
    password = _required("DATABASE_PASSWORD")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER=tcp:{server},1433;"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}"


engine = create_engine(
    build_connection_url(),
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """FastAPI database dependency."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def database_session():
    """Context manager useful outside FastAPI dependencies."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
