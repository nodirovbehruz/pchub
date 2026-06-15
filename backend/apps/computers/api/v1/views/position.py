"""Update Computer.position_x/position_y for the club map drag&drop editor."""

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.computers.models import Computer


class PositionSerializer(serializers.Serializer):
    position_x = serializers.IntegerField()
    position_y = serializers.IntegerField()


@extend_schema(tags=["Computers"])
class ComputerPositionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, computer_id):
        try:
            pc = Computer.objects.get(id=computer_id)
        except Computer.DoesNotExist:
            return Response({"detail": "PC not found"}, status=status.HTTP_404_NOT_FOUND)

        # SECURITY: was no ownership check — any authenticated user could move any
        # club's PC on the map (IDOR). Now verify the requester manages this PC's club.
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({"detail": "Нет прав на этот ПК"}, status=status.HTTP_403_FORBIDDEN)

        ser = PositionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        pc.position_x = ser.validated_data["position_x"]
        pc.position_y = ser.validated_data["position_y"]
        pc.save(update_fields=["position_x", "position_y"])
        return Response({"id": pc.id, "position_x": pc.position_x, "position_y": pc.position_y})
