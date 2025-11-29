from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.db.session import get_db
from app.domain.users.repository import UserRepository
from app.domain.users.schemas import TokenResponse, UserCreate, UserLogin, UserPublic
from app.domain.users.service import UserService

router = APIRouter()


@router.post("/auth/register", response_model=UserPublic)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserPublic:
    service = UserService(UserRepository(db))
    try:
        user = service.register(payload)
        db.commit()
        return UserPublic(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
        )
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    service = UserService(UserRepository(db))
    try:
        user = service.authenticate(payload.email, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)
