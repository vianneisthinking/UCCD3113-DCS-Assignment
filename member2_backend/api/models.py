"""
Database models and session handling.

The connection target comes from DATABASE_URL, so moving from local SQLite to
Member 4's cloud Postgres is an environment-variable change, not a code change.
"""

import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tickets.db")
DB_IAM_AUTH = os.getenv("DB_IAM_AUTH", "false").lower() == "true"

# check_same_thread is a SQLite-only quirk and is invalid for other engines.
connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

def _iam_postgres_connection():
    """Create one TLS PostgreSQL connection with a fresh RDS IAM token."""
    import boto3
    import psycopg2

    host = os.environ["DB_HOST"]
    port = int(os.getenv("DB_PORT", "5432"))
    username = os.getenv("DB_USER", "postgres")
    region = os.environ["AWS_REGION"]
    token = boto3.client("rds", region_name=region).generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=username,
        Region=region,
    )
    connection_options = {
        "host": host,
        "port": port,
        "dbname": os.getenv("DB_NAME", "postgres"),
        "user": username,
        "password": token,
        "sslmode": "verify-full",
        # Express clusters terminate TLS at the AWS internet access gateway,
        # whose certificate chains to the AWS/Amazon roots in Lambda's system
        # trust store rather than the regional RDS CA bundle.
        "sslrootcert": os.getenv(
            "DB_SSL_ROOT_CERT",
            "/etc/pki/tls/certs/ca-bundle.crt",
        ),
        "connect_timeout": 10,
    }

    # A 0-ACU express cluster can take longer than one connection timeout to
    # resume. The first attempt wakes it; one bounded retry lets the original
    # API request succeed without disabling auto-pause or adding paid network
    # infrastructure.
    for attempt in range(2):
        try:
            return psycopg2.connect(**connection_options)
        except psycopg2.OperationalError:
            if attempt == 1:
                raise
            time.sleep(1)


if DB_IAM_AUTH:
    engine = create_engine(
        "postgresql+psycopg2://",
        creator=_iam_postgres_connection,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
else:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


STATUSES = (
    "pending_classification",
    "open",
    "in_progress",
    "resolved",
    "closed",
)

OPEN_STATUSES = ("pending_classification", "open", "in_progress")


def utcnow():
    """Naive UTC timestamp — the format the API contract documents."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="customer")
    created_at = Column(DateTime, nullable=False, default=utcnow)

    tickets = relationship("Ticket", back_populates="user")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    complaint = Column(Text, nullable=False)

    # Routing decisions made by the backend.
    status = Column(String(30), nullable=False, index=True)
    department = Column(String(50), nullable=False, index=True)
    sla_due_at = Column(DateTime, nullable=False)

    # Classification results from Member 3's AI service.
    # All nullable: a ticket stored while the AI was down has none of them.
    category = Column(String(30), nullable=True)
    category_confidence = Column(Float, nullable=True)
    priority = Column(String(10), nullable=False)
    priority_confidence = Column(Float, nullable=True)
    model_version = Column(String(20), nullable=True)
    classified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow)

    user = relationship("User", back_populates="tickets")


def get_db():
    """FastAPI dependency yielding one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables if they do not exist. Deployed once from an empty database."""
    Base.metadata.create_all(bind=engine)
