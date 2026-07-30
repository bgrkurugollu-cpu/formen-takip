from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import decode_token, create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.auth_service import AccountLockedError, InactiveAccountError, InvalidCredentialsError, authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        _, access_token, refresh_token = authenticate(db, payload.email, payload.password, request.client.host if request.client else None)
    except AccountLockedError as exc:
        raise HTTPException(
            status.HTTP_423_LOCKED,
            f"Hesap çok sayıda başarısız denemeden dolayı geçici olarak kilitlendi. "
            f"Tekrar deneme zamanı: {exc.locked_until.isoformat()}",
        ) from exc
    except InactiveAccountError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-posta veya parola hatalı.") from exc

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_data = decode_token(payload.refresh_token)
    if token_data is None or token_data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Geçersiz veya süresi dolmuş yenileme jetonu.")

    user = db.get(User, token_data["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kullanıcı bulunamadı veya pasif.")

    new_access = create_access_token(str(user.id), {"email": user.email})
    return TokenResponse(access_token=new_access, refresh_token=payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user)) -> None:
    return None


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        title=current_user.title,
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    )
