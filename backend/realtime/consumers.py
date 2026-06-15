"""Realtime WebSocket consumer.

One socket per authenticated client (the C# shell) or operator (the React admin).
Carries everything that used to be polled — balance/time, notifications, remote
commands, guest-session entry — plus two-way chat, with zero delay.

Auth: JWT access token via the `?token=` query string (works for both the .NET
ClientWebSocket and the browser WebSocket API, neither of which can reliably set
Authorization headers cross-platform).

Groups joined:
  user_<user_id>   — direct pushes to this client (balance, personal messages)
  club_<club_id>   — club-wide broadcasts (operator chat, announcements)
"""

import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class ClientConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token = self._token_from_scope()
        self.user = await self._user_from_token(token)
        if self.user is None:
            await self.close(code=4001)  # unauthorized
            return

        self.user_group = f"user_{self.user.pk}"
        # Club comes from the query string (?club=) — the shell already knows it.
        qs = parse_qs((self.scope.get("query_string") or b"").decode())
        self.club_id = (qs.get("club") or [None])[0]
        self.club_group = f"club_{self.club_id}" if self.club_id else None

        # Operators get a private per-club group so client→operator chat reaches
        # the admin panel in realtime (clients are NOT in this group → no leak).
        # The club OWNER has user_type='user' (owns via Club.owner), so we must check
        # ownership/membership, not just user_type.
        self.is_operator = await self._is_operator_of(self.club_id)
        self.ops_group = f"club_ops_{self.club_id}" if (self.club_id and self.is_operator) else None

        await self.channel_layer.group_add(self.user_group, self.channel_name)
        if self.club_group:
            await self.channel_layer.group_add(self.club_group, self.channel_name)
        if self.ops_group:
            await self.channel_layer.group_add(self.ops_group, self.channel_name)

        await self.accept()
        await self.send(text_data=json.dumps({"type": "connected", "user_id": str(self.user.pk)}))

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            if getattr(self, "club_group", None):
                await self.channel_layer.group_discard(self.club_group, self.channel_name)
            if getattr(self, "ops_group", None):
                await self.channel_layer.group_discard(self.ops_group, self.channel_name)
        except Exception:
            pass

    async def receive(self, text_data=None, bytes_data=None):
        """Inbound from a client (shell). A chat message is STORED against the
        client's PC thread; the operator reads it from the admin chat panel. We do
        NOT rebroadcast to the whole club group (that would leak to other clients)."""
        try:
            data = json.loads(text_data or "{}")
        except Exception:
            return
        if data.get("type") == "chat":
            text = (data.get("text") or "").strip()
            if text:
                info = await self._store_client_chat(text)
                # Push to the club's operators in realtime (admin chat panel).
                if info and self.club_id:
                    await self.channel_layer.group_send(f"club_ops_{self.club_id}", {
                        "type": "chat.inbox",
                        "computer_id": info["computer_id"],
                        "computer_name": info["computer_name"],
                        "text": text,
                        "from_name": info["sender_name"],
                        "created_at": info["created_at"],
                    })

    @database_sync_to_async
    def _store_client_chat(self, text):
        try:
            from apps.computers.models import ChatMessage, Computer
            uname = getattr(self.user, "username", "") or ""
            pc = None
            if uname.startswith("guest-pc-"):
                try:
                    pc = Computer.objects.filter(id=int(uname.rsplit("-", 1)[1])).first()
                except (ValueError, IndexError):
                    pc = None
            if pc is None:
                hw = getattr(self.user, "active_hardware_id", "") or ""
                if hw:
                    pc = Computer.objects.filter(hardware_id=hw).first()
            if pc is None:
                return None
            name = "Гость" if uname.startswith("guest-pc-") else uname
            m = ChatMessage.objects.create(
                computer=pc, club_id=pc.club_id, sender=self.user,
                from_admin=False, sender_name=name, text=text, is_read=False,
            )
            return {
                "computer_id": pc.id, "computer_name": pc.name,
                "sender_name": name, "created_at": m.created_at.isoformat(),
            }
        except Exception:
            return None

    @database_sync_to_async
    def _is_operator_of(self, club_id):
        """True if this user can operate the club (owner / manager / operator /
        platform admin) — used to put them in the realtime operators group."""
        if not club_id:
            return False
        try:
            if getattr(self.user, "user_type", "") == "admin":
                return True
            from apps.clubs.models import Club, ClubMembership
            if Club.objects.filter(id=club_id, owner=self.user).exists():
                return True
            return ClubMembership.objects.filter(
                user=self.user, club_id=club_id, is_active=True,
                role__in=["owner", "manager", "operator"],
            ).exists()
        except Exception:
            return False

    # ── Group event handlers (names match the "type" of group_send payloads) ──
    async def balance_update(self, event):
        await self.send(text_data=json.dumps({"type": "balance", **event.get("data", {})}))

    async def notify(self, event):
        await self.send(text_data=json.dumps({"type": "notify", **event.get("data", {})}))

    async def command(self, event):
        await self.send(text_data=json.dumps({"type": "command", **event.get("data", {})}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat",
            "text": event.get("text", ""),
            "from_user_id": event.get("from_user_id"),
            "from_name": event.get("from_name"),
            "from_admin": event.get("from_admin", False),
        }))

    async def theme_update(self, event):
        # Live branding change from the admin → shell re-applies on the fly.
        await self.send(text_data=json.dumps({"type": "theme", **event.get("data", {})}))

    async def chat_inbox(self, event):
        # Client→operator chat delivered live to the admin chat panel.
        await self.send(text_data=json.dumps({
            "type": "chat_inbox",
            "computer_id": event.get("computer_id"),
            "computer_name": event.get("computer_name"),
            "text": event.get("text", ""),
            "from_name": event.get("from_name"),
            "created_at": event.get("created_at"),
        }))

    async def order_new(self, event):
        # New shop order → operator's admin panel (club group).
        await self.send(text_data=json.dumps({"type": "order_new", **event.get("data", {})}))

    async def order_status(self, event):
        # Order status change → client's shell.
        await self.send(text_data=json.dumps({"type": "order_status", **event.get("data", {})}))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _token_from_scope(self):
        qs = parse_qs((self.scope.get("query_string") or b"").decode())
        if qs.get("token"):
            return qs["token"][0]
        for name, value in self.scope.get("headers", []):
            if name == b"authorization":
                raw = value.decode()
                if raw.lower().startswith("bearer "):
                    return raw[7:]
        return None

    @database_sync_to_async
    def _user_from_token(self, token):
        if not token:
            return None
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            access = AccessToken(token)
            User = get_user_model()
            return User.objects.filter(pk=access["user_id"]).first()
        except Exception:
            return None
