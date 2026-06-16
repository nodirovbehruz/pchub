from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions

from apps.clubs.api.v1.mixins import TenantFilterMixin, TenantCreateMixin, validated_club_id
from apps.computers.api.v1.serializers.group import ComputerGroupSerializer
from apps.computers.models import ComputerGroup


@extend_schema(tags=["Computer Groups"])
class ComputerGroupListCreateAPIView(TenantCreateMixin, generics.ListCreateAPIView):
    """List and create computer groups (zones) for a club. Create is forced into the
    authorized club (was trusting body `club`)."""

    serializer_class = ComputerGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # SECURITY: was trusting raw ?club= with no membership check, so any authenticated
        # user could read another club's zones by passing its id. Scope to a club the
        # caller actually belongs to (validated_club_id checks membership).
        cid = validated_club_id(self.request)
        if not cid:
            return ComputerGroup.objects.none()
        return (ComputerGroup.objects.filter(is_active=True, club_id=cid)
                .select_related("club").order_by("position", "name"))


@extend_schema(tags=["Computer Groups"])
class ComputerGroupDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a computer group — tenant-scoped (IDOR fix)."""

    serializer_class = ComputerGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ComputerGroup.objects.all()
    lookup_url_kwarg = "group_id"
