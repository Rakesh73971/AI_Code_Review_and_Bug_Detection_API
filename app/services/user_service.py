from sqlalchemy.orm import Session
from app.models.user import User
from fastapi import HTTPException,status
from app.core.utils import hash_password


def create_user_service(db:Session,user):
    db_user = User(
        username = user.username,
        email = user.email,
        password = hash_password(user.password),
        role = user.role,
        github_name = user.github_name if user.github_name is not None else None,
        is_active = user.is_active if user.is_active is not None else True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
    
def get_users_service(db:Session):
    return db.query(User).all()

def get_user_service(db:Session,user_id:int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"user with id {user_id} not found")
    return db_user

def update_user_service(db:Session,user_id:int,user_update):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"user with id {user_id} not found")
    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["password"] = hash_password(update_data["password"])

    for key,value in update_data.items():
        setattr(db_user,key,value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user_service(db:Session,user_id):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"user with id {user_id} not found")
    db.delete(db_user)
    db.commit()
    
    return None
