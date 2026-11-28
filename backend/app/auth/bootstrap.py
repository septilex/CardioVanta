"""Explicit operator-only initial admin assignment; no default account/password or HTTP backdoor."""
import argparse
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.orm import engine, User, Role
from backend.app.auth.security import revoke

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grant admin to an existing registered account using operator DB access.")
    parser.add_argument("email")
    args = parser.parse_args()
    with Session(engine(settings.require_secret("DATABASE_URL"))) as db:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if not user:
            parser.error("Register the account first.")
        user.roles = [db.get(Role, "admin")]
        revoke(db, user)
        db.commit()
    print("Administrator role granted. Sign in again.")
