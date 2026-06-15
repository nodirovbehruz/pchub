from typing import Any, Dict

from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.repositories.interface.account import IAccountRepository
from apps.accounts.services.interface.auth import IAuthService


class SessionAlreadyActiveError(PermissionDenied):
    """Raised when a user tries to login while already active on another PC."""
    default_detail = "Этот аккаунт уже активен на другом компьютере."
    default_code = "session_already_active"


class AuthService(IAuthService):
    def __init__(self, account_repository: IAccountRepository):
        self.account_repository = account_repository

    def login_user(self, username: str, password: str, hardware_id: str = None) -> Dict[str, Any]:
        """Authenticate user and generate tokens"""

        # Get user
        user = self.account_repository.get_user_by_username(username)
        if not user:
            raise ValidationError({"email": "No account found with this email address"})

        # Verify password
        if not user.check_password(password):
            raise ValidationError({"password": "Incorrect password"})

        # Check if user is active
        if not user.is_active:
            raise ValidationError(
                {
                    "email": "Account is not activated. Please check your email for verification instructions."
                }
            )

        # ── Parallel session protection ───────────────────────────────────────
        # Allow login if:
        # 1. User is admin
        # 2. Session is not active
        # 3. Session is active but it's the SAME hardware (crash recovery)
        # 4. Session is active but NO ACTIVITY for > 5 minutes (stale session cleanup)
        if user.is_active_session and user.user_type != "admin":
            is_same_hardware = hardware_id and user.active_hardware_id == hardware_id
            
            is_stale = False
            if user.last_activity:
                is_stale = (timezone.now() - user.last_activity) > timedelta(seconds=90)

            if not is_same_hardware and not is_stale:
                raise SessionAlreadyActiveError()

        # Mark user as having an active session and update activity
        user.is_active_session = True
        user.active_hardware_id = hardware_id
        user.last_activity = timezone.now()
        user.save(update_fields=["is_active_session", "active_hardware_id", "last_activity"])
        # ─────────────────────────────────────────────────────────────────────

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": user,
        }

    def logout_user(self, refresh_token: str, user=None) -> None:
        """Blacklist refresh token to logout user"""

        if not refresh_token:
            raise ValidationError({"refresh": "Refresh token is required"})

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            raise ValidationError({"refresh": "Invalid or expired token"})

        # Clear active session flag
        if user is not None and hasattr(user, "is_active_session"):
            user.is_active_session = False
            user.save(update_fields=["is_active_session"])
