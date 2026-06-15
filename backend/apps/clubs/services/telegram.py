"""Telegram notification service for PCHub clubs.

Usage:
    from apps.clubs.services.telegram import notify_club
    notify_club(club_id, "🔓 Смена открыта оператором Иван")
"""
from __future__ import annotations

import logging
import urllib.request
import json

logger = logging.getLogger(__name__)


def _get_settings(club_id) -> tuple[str | None, str | None]:
    """Return (bot_token, chat_id) from ClubSettings.data or (None, None)."""
    try:
        from apps.clubs.models import ClubSettings
        obj = ClubSettings.objects.get(club_id=club_id)
        data = obj.data or {}
        token   = data.get("telegram_bot_token", "").strip()
        chat_id = data.get("telegram_chat_id",   "").strip()
        return (token or None, chat_id or None)
    except Exception:
        return None, None


def notify_club(club_id, text: str) -> bool:
    """Send a Telegram message to the club's configured channel.

    Returns True if sent successfully, False otherwise (never raises).
    """
    token, chat_id = _get_settings(club_id)
    if not token or not chat_id:
        return False  # not configured — silently skip

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                logger.warning("Telegram API error for club %s: %s", club_id, result)
                return False
        return True
    except Exception as exc:
        logger.warning("Telegram send failed for club %s: %s", club_id, exc)
        return False


def test_notify(club_id) -> tuple[bool, str]:
    """Send a test message. Returns (success, error_message)."""
    token, chat_id = _get_settings(club_id)
    if not token:
        return False, "Токен бота не указан"
    if not chat_id:
        return False, "Chat ID не указан"

    ok = notify_club(club_id, "✅ <b>PCHub</b> — тестовое сообщение. Интеграция работает!")
    if ok:
        return True, ""
    return False, "Не удалось отправить. Проверьте токен и Chat ID."
