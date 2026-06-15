"""Operator↔PC private chat (admin side).

Client (shell) messages arrive over the WebSocket and are stored by the realtime
consumer. Operators read threads / reply here; replies are pushed to the client's
shell instantly via realtime, and persisted.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.computers.models import ChatMessage, Computer


def _operator_can(user, club_id):
    if getattr(user, "is_admin", False) or getattr(user, "user_type", "") == "admin":
        return True
    if not club_id:
        return False
    from apps.clubs.models import Club, ClubMembership
    return Club.objects.filter(id=club_id, owner=user).exists() or ClubMembership.objects.filter(
        user=user, club_id=club_id, is_active=True, role__in=["owner", "manager", "operator"]
    ).exists()


def _ser(m):
    return {
        "id": m.id,
        "from_admin": m.from_admin,
        "sender_name": m.sender_name or ("Оператор" if m.from_admin else "Гость"),
        "text": m.text,
        "is_read": m.is_read,
        "created_at": m.created_at,
    }


class AdminChatThreadsAPIView(APIView):
    """GET /api/v1/computers/admin/chat/?club=<id> — one entry per PC that has
    chat history, with last message + unread (client→operator) count."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        club_id = getattr(request, "current_club_id", None) or request.query_params.get("club")
        if not _operator_can(request.user, club_id):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        from django.db.models import Count, Max, Q
        rows = (
            ChatMessage.objects.filter(club_id=club_id)
            .values("computer_id", "computer__name")
            .annotate(
                last_at=Max("created_at"),
                unread=Count("id", filter=Q(from_admin=False, is_read=False)),
                total=Count("id"),
            )
            .order_by("-last_at")
        )
        threads = []
        for r in rows:
            last = (
                ChatMessage.objects.filter(computer_id=r["computer_id"], club_id=club_id)
                .order_by("-created_at").first()
            )
            threads.append({
                "computer_id": r["computer_id"],
                "computer_name": r["computer__name"],
                "unread": r["unread"],
                "total": r["total"],
                "last_text": last.text if last else "",
                "last_at": r["last_at"],
            })
        return Response(threads)


class AdminChatMessagesAPIView(APIView):
    """GET  …/admin/chat/<computer_id>/  — full thread (marks client msgs read).
       POST …/admin/chat/<computer_id>/  — operator sends a reply."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, computer_id):
        try:
            pc = Computer.objects.get(id=computer_id)
        except Computer.DoesNotExist:
            return Response({"error": "ПК не найден"}, status=status.HTTP_404_NOT_FOUND)
        if not _operator_can(request.user, pc.club_id):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        qs = ChatMessage.objects.filter(computer_id=computer_id).order_by("created_at")
        # Mark incoming (client) messages as read now that the operator opened it.
        ChatMessage.objects.filter(computer_id=computer_id, from_admin=False, is_read=False).update(is_read=True)
        return Response([_ser(m) for m in qs[:300]])

    def post(self, request, computer_id):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"error": "Пустое сообщение"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pc = Computer.objects.get(id=computer_id)
        except Computer.DoesNotExist:
            return Response({"error": "ПК не найден"}, status=status.HTTP_404_NOT_FOUND)
        if not _operator_can(request.user, pc.club_id):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        op_name = getattr(request.user, "username", "Оператор")
        msg = ChatMessage.objects.create(
            computer=pc, club_id=pc.club_id, sender=request.user,
            from_admin=True, sender_name=op_name, text=text, is_read=False,
        )

        # Deliver instantly to whoever is at the PC (guest or logged-in client).
        from apps.accounts.models import CustomUser
        from realtime.broadcast import push_chat_to_user
        targets = set()
        guest = CustomUser.objects.filter(username=f"guest-pc-{pc.id}").first()
        if guest:
            targets.add(guest.pk)
        if pc.hardware_id:
            for cu in CustomUser.objects.filter(active_hardware_id=pc.hardware_id, is_active_session=True):
                targets.add(cu.pk)
        for uid in targets:
            try:
                push_chat_to_user(uid, text=text, from_name=op_name, from_admin=True)
            except Exception:
                pass

        return Response(_ser(msg), status=status.HTTP_201_CREATED)
