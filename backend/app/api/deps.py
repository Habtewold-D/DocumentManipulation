from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import TokenError, decode_access_token
from app.db.session import get_db
from app.domain.users.repository import UserRepository


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
    access_token_cookie: str | None = Cookie(default=None, alias="pdf_agent_token"),
) -> str:
    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", maxsplit=1)[1]
    elif access_token_cookie:
        token = access_token_cookie

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        user_id = decode_access_token(token)
    except TokenError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user.id
