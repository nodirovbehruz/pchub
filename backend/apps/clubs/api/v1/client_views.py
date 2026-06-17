"""Client groups + client comments endpoints (SmartShell-style Clients page)."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


def _club_id(request):
    """SECURITY: resolve the club ONLY after re-checking that request.user is the
    owner / active member / platform admin of it. Was trusting the raw
    current_club_id / ?club= / body `club` with no membership check, so any
    authenticated user could read, edit or delete another club's client groups and
    operator comments by passing a foreign club id."""
    from apps.clubs.api.v1.mixins import validated_club_id
    return validated_club_id(request)


# ── Client Groups ──────────────────────────────────────────────────────────
class ClientGroupListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.clubs.models import ClientGroup, UserClubProfile
        club_id = _club_id(request)
        if not club_id:
            return Response([])
        groups = ClientGroup.objects.filter(club_id=club_id).order_by("name")
        out = []
        for g in groups:
            out.append({
                "id": g.id,
                "name": g.name,
                "percent_discount": g.percent_discount,
                "members_count": UserClubProfile.objects.filter(club_id=club_id, group=g).count(),
            })
        return Response(out)

    def post(self, request):
        from apps.clubs.models import ClientGroup
        club_id = _club_id(request)
        name = (request.data.get("name") or "").strip()
        if not club_id:
            return Response({"error": "club required or no access"}, status=status.HTTP_403_FORBIDDEN)
        if not name:
            return Response({"error": "Название обязательно"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            discount = int(request.data.get("percent_discount", 0) or 0)
        except (TypeError, ValueError):
            discount = 0
        discount = max(0, min(100, discount))
        # Truncate BEFORE the uniqueness check — the check used the full name but the row
        # was created with name[:16], so two long names sharing a 16-char prefix passed
        # the check and then collided on the unique constraint → IntegrityError 500.
        name = name[:16]
        if ClientGroup.objects.filter(club_id=club_id, name=name).exists():
            return Response({"error": "Группа с таким именем уже существует"}, status=status.HTTP_400_BAD_REQUEST)
        g = ClientGroup.objects.create(club_id=club_id, name=name, percent_discount=discount)
        return Response({"id": g.id, "name": g.name, "percent_discount": g.percent_discount, "members_count": 0},
                        status=status.HTTP_201_CREATED)


class ClientGroupDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        from apps.clubs.models import ClientGroup, UserClubProfile
        club_id = _club_id(request)
        if not club_id:
            return Response({"error": "club required or no access"}, status=status.HTTP_403_FORBIDDEN)
        try:
            # SECURITY: constrain to the authorized club (was ClientGroup.objects.get(pk)
            # — cross-club IDOR: any user could rename/re-discount another club's group).
            g = ClientGroup.objects.get(pk=pk, club_id=club_id)
        except ClientGroup.DoesNotExist:
            return Response({"error": "Группа не найдена"}, status=status.HTTP_404_NOT_FOUND)
        if "name" in request.data:
            name = (request.data["name"] or "").strip()
            if name:
                g.name = name[:16]
        if "percent_discount" in request.data:
            try:
                g.percent_discount = max(0, min(100, int(request.data["percent_discount"])))
            except (TypeError, ValueError):
                pass
        g.save(update_fields=["name", "percent_discount"])
        return Response({"id": g.id, "name": g.name, "percent_discount": g.percent_discount,
                         "members_count": UserClubProfile.objects.filter(club_id=club_id, group=g).count()})

    def delete(self, request, pk):
        from apps.clubs.models import ClientGroup
        club_id = _club_id(request)
        if not club_id:
            return Response({"error": "club required or no access"}, status=status.HTTP_403_FORBIDDEN)
        try:
            g = ClientGroup.objects.get(pk=pk, club_id=club_id)
        except ClientGroup.DoesNotExist:
            return Response({"error": "Группа не найдена"}, status=status.HTTP_404_NOT_FOUND)
        g.delete()  # members.group set to NULL via on_delete=SET_NULL
        return Response({"success": True})


class ClientAssignGroupAPIView(APIView):
    """PATCH /clients/<user_id>/group/  body: { group: <id|null>, club }"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, user_id):
        from apps.clubs.models import ClientGroup, UserClubProfile
        club_id = _club_id(request)
        if not club_id:
            return Response({"error": "club required or no access"}, status=status.HTTP_403_FORBIDDEN)
        try:
            profile = UserClubProfile.objects.get(user_id=user_id, club_id=club_id)
        except UserClubProfile.DoesNotExist:
            return Response({"error": "Профиль не найден"}, status=status.HTTP_404_NOT_FOUND)
        group_id = request.data.get("group")
        if group_id:
            # SECURITY: the group must belong to THIS club — was assigned blindly, so a
            # foreign group's discount leaked in (and a bad id raised a 500 IntegrityError).
            if not ClientGroup.objects.filter(id=group_id, club_id=club_id).exists():
                return Response({"error": "Группа не найдена в этом клубе"}, status=status.HTTP_400_BAD_REQUEST)
        profile.group_id = group_id or None
        profile.save(update_fields=["group"])
        return Response({"success": True, "group": profile.group_id})


# ── Client Comments ────────────────────────────────────────────────────────
class ClientCommentListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        from apps.clubs.models import ClientComment
        club_id = _club_id(request)
        # SECURITY: require an authorized club — was returning this client's operator
        # notes from EVERY club when no club context was given (cross-club PII leak).
        if not club_id:
            return Response([])
        qs = (ClientComment.objects.filter(client_id=user_id, club_id=club_id)
              .select_related("author"))
        return Response([{
            "id": c.id,
            "text": c.text,
            "is_important": c.is_important,
            "author": c.author.username if c.author else "—",
            "created_at": c.created_at.isoformat(),
        } for c in qs])

    def post(self, request, user_id):
        from apps.clubs.models import ClientComment
        club_id = _club_id(request)
        text = (request.data.get("text") or "").strip()
        if not club_id:
            return Response({"error": "club required or no access"}, status=status.HTTP_403_FORBIDDEN)
        if not text:
            return Response({"error": "Комментарий пуст"}, status=status.HTTP_400_BAD_REQUEST)
        c = ClientComment.objects.create(
            club_id=club_id, client_id=user_id,
            author=request.user if request.user.is_authenticated else None,
            text=text, is_important=bool(request.data.get("is_important", False)),
        )
        return Response({
            "id": c.id, "text": c.text, "is_important": c.is_important,
            "author": c.author.username if c.author else "—",
            "created_at": c.created_at.isoformat(),
        }, status=status.HTTP_201_CREATED)


class ClientCommentDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        from apps.clubs.models import ClientComment
        club_id = _club_id(request)
        if not club_id:
            return Response({"error": "club required or no access"}, status=status.HTTP_403_FORBIDDEN)
        try:
            # SECURITY: scope to the authorized club (was ClientComment.objects.get(pk)
            # — cross-club IDOR on operator notes).
            c = ClientComment.objects.get(pk=pk, club_id=club_id)
        except ClientComment.DoesNotExist:
            return Response({"error": "Не найдено"}, status=status.HTTP_404_NOT_FOUND)
        if "is_important" in request.data:
            c.is_important = bool(request.data["is_important"])
        if "text" in request.data:
            t = (request.data["text"] or "").strip()
            if t:
                c.text = t
        c.save(update_fields=["is_important", "text"])
        return Response({"id": c.id, "text": c.text, "is_important": c.is_important})

    def delete(self, request, pk):
        from apps.clubs.models import ClientComment
        club_id = _club_id(request)
        if not club_id:
            return Response({"error": "club required or no access"}, status=status.HTTP_403_FORBIDDEN)
        deleted, _ = ClientComment.objects.filter(pk=pk, club_id=club_id).delete()
        if not deleted:
            return Response({"error": "Не найдено"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True})
