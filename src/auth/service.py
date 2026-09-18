"""
Authentication logic: password hashing and business signup/login.

Passwords are only ever stored as bcrypt hashes (Core Rule #3). Nothing in
this module logs a password, a hash, or the session secret.
"""
from __future__ import annotations

from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from src.db.models import Business


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash - never crash the login flow over it.
        return False


def get_business_by_email(db: Session, email: str) -> Optional[Business]:
    return db.query(Business).filter(Business.email == email).first()


def create_business(
    db: Session,
    name: str,
    owner_name: str,
    email: str,
    password: str,
    category: Optional[str] = None,
) -> Business:
    """
    Create a new business account.

    Callers are expected to have already validated the input (see
    `src.core.validation.validate_signup`) and checked that the email is
    not already registered; this function does not repeat those checks so
    that validation errors can be surfaced to the user before any DB work.
    """
    password_hash = hash_password(password)
    business = Business(
        name=name,
        owner_name=owner_name,
        email=email,
        password_hash=password_hash,
        category=category,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def authenticate_business(db: Session, email: str, password: str) -> Optional[Business]:
    business = get_business_by_email(db, email)
    if business and verify_password(password, business.password_hash):
        return business
    return None
