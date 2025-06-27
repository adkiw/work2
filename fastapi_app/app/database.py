import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:password@localhost/appdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def set_current_tenant(db: Session, tenant_id: str) -> None:
    """Set the session variable used by row-level security policies."""
    db.execute(text("SET app.current_tenant = :tenant"), {"tenant": tenant_id})
