from fastapi import status,Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.config import settings
from jose import jwt,JWTError
from datetime import datetime,timedelta
from app.schemas.user import TokenData
from app.db.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes



def create_access_token(data:dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    return jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)


def verify_access_token(token:str,credential_exceptions):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id:int = payload.get("user_id")
        if user_id is None:
            raise credential_exceptions
        
        token_data = TokenData(id=user_id)
        return token_data
    except JWTError:
        raise credential_exceptions
    
def get_current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(get_db)):
    credential_exceptions = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='could not validate credentials',
        headers={'WWW-Authenticate':'Bearer'}
    )

    token_data = verify_access_token(token,credential_exceptions)

    user = db.query(User).filter(User.id == token_data.id).first()
    if user is None:
        raise credential_exceptions
    
    return user

def get_admin_user(current_user:User=Depends(get_current_user)):
    role_value = current_user.role.value if hasattr(current_user.role,'value') else current_user.role
    if role_value != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You do not have enough privileges'
        ) 
    return current_user