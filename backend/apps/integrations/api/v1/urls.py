from django.urls import path
from rest_framework import generics, permissions, serializers as drf_serializers

from apps.clubs.api.v1.mixins import TenantFilterMixin
from apps.integrations.models import (
    BlockedApp,
    Integration,
    ShellSecurity,
    ShellTheme,
)


class IntegrationSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "last_test_at", "last_test_ok"]


class ShellThemeSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = ShellTheme
        fields = "__all__"


class BlockedAppSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = BlockedApp
        fields = ["id", "security", "name_mask", "window_class", "note"]


class ShellSecuritySerializer(drf_serializers.ModelSerializer):
    blocked_apps = BlockedAppSerializer(many=True, read_only=True)

    class Meta:
        model = ShellSecurity
        fields = "__all__"


class IntegrationListCreateAPIView(TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = IntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Integration.objects.all()


class IntegrationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = IntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Integration.objects.all()


class ShellThemeDetailAPIView(generics.RetrieveUpdateAPIView):
    """Single-instance per club, lookup by club_id."""
    serializer_class = ShellThemeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ShellTheme.objects.all()
    lookup_field = "club_id"


class ShellSecurityDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ShellSecuritySerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ShellSecurity.objects.all()
    lookup_field = "club_id"

    def get_object(self):
        # get_or_create so the shell (and admin panel) never 404 on a club whose
        # ShellSecurity row was never created — it's auto-made with safe defaults
        # (high_access_password="pasw0rd"). Without this the shell can't read the
        # per-club admin/exit code and falls back to the local default.
        obj, _ = ShellSecurity.objects.get_or_create(club_id=self.kwargs["club_id"])
        return obj


class BlockedAppListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = BlockedAppSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = BlockedApp.objects.all()


class BlockedAppDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BlockedAppSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = BlockedApp.objects.all()


app_name = "integrations"

urlpatterns = [
    path("", IntegrationListCreateAPIView.as_view(), name="list"),
    path("<int:pk>/", IntegrationDetailAPIView.as_view(), name="detail"),
    path("themes/<int:club_id>/", ShellThemeDetailAPIView.as_view(), name="theme-detail"),
    path("security/<int:club_id>/", ShellSecurityDetailAPIView.as_view(), name="security-detail"),
    path("blocked-apps/", BlockedAppListCreateAPIView.as_view(), name="blocked-app-list"),
    path("blocked-apps/<int:pk>/", BlockedAppDetailAPIView.as_view(), name="blocked-app-detail"),
]
