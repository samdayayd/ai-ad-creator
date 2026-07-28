"""Creates the app owner's account from OWNER_EMAIL/OWNER_PASSWORD if it
doesn't exist yet, on the unlimited OWNER_PLAN so the person running this
tool never hits the same quota paying customers do. Run once on first
deploy (or automatically — see main.py's startup hook). Everyone else signs
up for a real account via POST /api/auth/signup instead."""

from app.auth import hash_password
from app.config import OWNER_EMAIL, OWNER_PASSWORD, OWNER_PLAN
from app.db import SessionLocal, User, init_db


def seed():
    init_db()
    session = SessionLocal()
    try:
        email = OWNER_EMAIL.strip().lower()
        existing = session.query(User).filter(User.email == email).first()
        if not existing:
            session.add(User(email=email, hashed_password=hash_password(OWNER_PASSWORD), plan=OWNER_PLAN))
            session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
