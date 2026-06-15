"""Push helpers callable from ordinary (sync) Django views/services.

Fire-and-forget: never raise into the caller — a realtime hiccup must not break
the underlying HTTP action (topup, deduct, etc.). The client also still has a
slow polling fallback, so a dropped push self-heals on the next poll.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def _send(group: str, payload: dict) -> None:
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(group, payload)
    except Exception:
        pass  # realtime is best-effort


def push_balance(user_id, data: dict) -> None:
    """Instant balance/time update to a specific client."""
    _send(f"user_{user_id}", {"type": "balance.update", "data": data})


def push_notify(user_id, data: dict) -> None:
    """Instant notification to a specific client."""
    _send(f"user_{user_id}", {"type": "notify", "data": data})


def push_command(user_id, data: dict) -> None:
    """Instant remote command to a specific client (lock/unlock/etc.)."""
    _send(f"user_{user_id}", {"type": "command", "data": data})


def push_order(club_id, data: dict) -> None:
    """New shop order waiting for the operator. Delivered ONLY to the club's
    operators group (club_ops_<id>) — NOT club_<id>, which clients also join via
    ?club= and would otherwise leak order/customer data cross-tenant."""
    _send(f"club_ops_{club_id}", {"type": "order.new", "data": data})


def push_order_status(user_id, data: dict) -> None:
    """Order status change (paid / preparing / delivered) to the client's shell."""
    _send(f"user_{user_id}", {"type": "order.status", "data": data})


def push_theme(club_id, data: dict) -> None:
    """Live branding/theme update to every shell connected to a club, so an admin
    change (accent, background, logo) applies on the fly without a re-login."""
    _send(f"club_{club_id}", {"type": "theme.update", "data": data})


def push_chat_to_user(user_id, text: str, from_name: str, from_admin: bool) -> None:
    """Private chat delivery to ONE user (the client at a PC). Reuses the shell's
    existing chat_message handler so the message pops in the shell chat instantly."""
    _send(f"user_{user_id}", {
        "type": "chat.message",
        "text": text,
        "from_user_id": None,
        "from_name": from_name,
        "from_admin": from_admin,
    })


def push_club_chat(club_id, text: str, from_name: str, from_admin: bool, from_user_id=None) -> None:
    """Broadcast a chat message to everyone in a club (operators + clients)."""
    _send(f"club_{club_id}", {
        "type": "chat.message",
        "text": text,
        "from_user_id": str(from_user_id) if from_user_id else None,
        "from_name": from_name,
        "from_admin": from_admin,
    })
