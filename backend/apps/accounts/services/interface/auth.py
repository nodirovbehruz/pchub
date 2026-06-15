from typing import Any, Dict, Protocol


class IAuthService(Protocol):
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user and generate tokens"""
        ...

    def logout_user(self, refresh_token: str) -> None:
        """Blacklist refresh token to logout user"""
        ...
