
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.user import User
from app.services.audit import record_audit

settings = get_settings()


class AuthenticationError(Exception):
    pass


class AccountLockedError(AuthenticationError):
    def __init__(self, locked_until: datetime) -> None:
        self.locked_until = locked_until
        super().__init__(f"Hesap {locked_until.isoformat()} tarihine kadar kilitli.")


class InvalidCredentialsError(AuthenticationError):
    pass


class InactiveAccountError(AuthenticationError):
    pass


def _log(db: Session, user_id: UUID | None, action: str, success: bool, ip: str | None, error: str | None = None) -> None:
    record_audit(db, user_id, action, entity="auth", ip_address=ip, success=success, error_message=error)


def authenticate(db: Session, email: str, password: str, ip_address: str | None = None) -> tuple[User, str, str]:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        _log(db, None, "login_failed", False, ip_address, "Kullanıcı bulunamadı")
        raise InvalidCredentialsError("E-posta veya parola hatalı.")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        _log(db, user.id, "login_failed", False, ip_address, "Hesap kilitli")
        raise AccountLockedError(user.locked_until)

    if not user.is_active:
        _log(db, user.id, "login_failed", False, ip_address, "Hesap pasif")
        raise InactiveAccountError("Hesap pasif durumda.")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
        db.commit()
        _log(db, user.id, "login_failed", False, ip_address, "Hatalı parola")
        raise InvalidCredentialsError("E-posta veya parola hatalı.")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    _log(db, user.id, "login_success", True, ip_address)

    access_token = create_access_token(str(user.id), {"email": user.email})
    refresh_token = create_refresh_token(str(user.id))
    return user, access_token, refresh_token


def change_password(db: Session, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    db.commit()
