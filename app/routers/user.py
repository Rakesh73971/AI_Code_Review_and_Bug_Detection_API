from fastapi import APIRouter,status,Depends
from sqlalchemy.orm import Session
from app.services.user_service import create_user_service,get_users_service,get_user_service,update_user_service,delete_user_service
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.db.database import get_db
from typing import List
from app.core.oauth2 import get_admin_user,get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/",status_code=status.HTTP_201_CREATED,response_model=UserResponse)
def create_user(user:UserCreate,db:Session=Depends(get_db)):
    return create_user_service(db,user)

@router.get("/",status_code=status.HTTP_200_OK,response_model=List[UserResponse])
def get_users(db:Session=Depends(get_db),current_user=Depends(get_admin_user)):
    return get_users_service(db)

@router.get("/{user_id}",status_code=status.HTTP_200_OK,response_model=UserResponse)
def get_user(user_id:int,db:Session=Depends(get_db),current_user=Depends(get_admin_user)):
    return get_user_service(db,user_id)

@router.put("/{user_id}",status_code=status.HTTP_200_OK,response_model=UserResponse)
def update_user(user_id:int,user:UserUpdate,db:Session=Depends(get_db),current_user=Depends(get_current_user)):
    return update_user_service(db,user_id,user)

@router.delete("/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id:int,db:Session=Depends(get_db),current_user=Depends(get_current_user)):
    return delete_user_service(db,user_id)