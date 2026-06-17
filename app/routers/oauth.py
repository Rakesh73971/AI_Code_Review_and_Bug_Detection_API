from fastapi import APIRouter,status,Depends,HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import User
from app.core import oauth2,utils
from app.db.database import get_db

router = APIRouter(tags=['Authentication'])


@router.post("/login")
def login_user(
    user_credentials:OAuth2PasswordRequestForm=Depends(),
    db:Session=Depends()
):
    user = db.query(User).filter(User.email == user_credentials.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Invalid Credentials")
    
    if not utils.verify_passwords(user_credentials.password,user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Invalid Credentials")
    