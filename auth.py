import bcrypt
from sqlalchemy.orm import Session
from models import Business


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_business(db: Session, name: str, owner_name: str, email: str, password: str, category: str = None) -> Business:
    password_hash = hash_password(password)
    business = Business(
        name=name,
        owner_name=owner_name,
        email=email,
        password_hash=password_hash,
        category=category
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def authenticate_business(db: Session, email: str, password: str) -> Business:
    business = db.query(Business).filter(Business.email == email).first()
    if business and verify_password(password, business.password_hash):
        return business
    return None


def get_business_by_email(db: Session, email: str) -> Business:
    return db.query(Business).filter(Business.email == email).first()
