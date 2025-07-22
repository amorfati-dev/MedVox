"""
Database session management and configuration
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Create database engine
engine = create_engine(
    settings.database.DATABASE_URL,
    echo=settings.database.ECHO_SQL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Use this in FastAPI endpoints:
    
    @app.get("/items/")
    def read_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 