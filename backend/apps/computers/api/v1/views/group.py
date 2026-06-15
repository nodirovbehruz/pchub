from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions

from apps.clubs.api.v1.mixins import TenantFilterMixin, TenantCreateMixin
from apps.computers.api.v1.serializers.group import ComputerGroupSerializer
from apps.computers.models import ComputerGroup


@extend_schema(tags=["Computer Groups"])
class ComputerGroupListCreateAPIView(TenantCreateMixin, generics.ListCreateAPIView):
    """List and create computer groups (zones) for a club. Create is forced into the
    authorized club (was trusting body `club`)."""

    serializer_class = ComputerGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ComputerGroup.objects.filter(is_active=True).select_related("club")
        club_id = self.request.query_params.get("club")
        if club_id:
            qs = qs.filter(club_id=club_id)
        return qs.order_by("club_id", "position", "name")


@extend_schema(tags=["Computer Groups"])
class ComputerGroupDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a computer group — tenant-scoped (IDOR fix)."""

    serializer_class = ComputerGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ComputerGroup.objects.all()
    lookup_url_kwarg = "group_id"
