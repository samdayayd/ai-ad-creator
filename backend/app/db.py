from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class AdGeneration(Base):
    """One "Create ads" click, kept as history so the owner can revisit past
    generations instead of re-spending an API call to see them again."""

    __tablename__ = "ad_generations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_url = Column(String, nullable=False)
    product_title = Column(String, nullable=True)
    product_image = Column(String, nullable=True)
    result_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class VideoGeneration(Base):
    """One rendered video ad. The file itself lives on disk (VIDEO_STORAGE_DIR)
    — this row is just enough metadata to list/stream it back without
    re-rendering."""

    __tablename__ = "video_generations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_title = Column(String, nullable=True)
    requested_duration_seconds = Column(Integer, nullable=False)
    actual_duration_seconds = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    scenes_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UGCGeneration(Base):
    """One rendered UGC-style presenter ad — a D-ID talking presenter clip
    edited together with product-photo cutaways and a CTA card. Same
    on-disk-file-plus-metadata-row pattern as VideoGeneration."""

    __tablename__ = "ugc_generations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_title = Column(String, nullable=True)
    presenter_name = Column(String, nullable=False)
    voice_name = Column(String, nullable=False)
    cta_text = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    script_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
