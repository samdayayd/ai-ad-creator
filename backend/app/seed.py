"""Creates the single owner account from OWNER_EMAIL/OWNER_PASSWORD if it
doesn't exist yet. Run once on first deploy (or automatically — see main.py's
startup hook)."""

from app.auth import hash_password
from app.config import OWNER_EMAIL, OWNER_PASSWORD
from app.db import SessionLocal, User, init_db


def seed():
    init_db()
    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.email == OWNER_EMAIL).first()
        if not existing:
            session.add(User(email=OWNER_EMAIL, hashed_password=hash_password(OWNER_PASSWORD)))
            session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
