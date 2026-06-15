from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.clubs.api.v1.mixins import TenantFilterMixin
from apps.sessions_.api.v1.serializers import (
    AdminCallSerializer,
    ClientSessionSerializer,
    ReviewSerializer,
)
from apps.sessions_.models import AdminCall, ClientSession, Review


class ClientSessionListAPIView(TenantFilterMixin, generics.ListAPIView):
    serializer_class = ClientSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ClientSession.objects.all().prefetch_related("hosts").select_related("client", "tariff")

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class ClientSessionDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateAPIView):
    """Tenant-scoped — was ClientSession.objects.all() with no club filter, so any
    operator could GET/PATCH another club's session by id (IDOR + PII leak)."""
    serializer_class = ClientSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ClientSession.objects.all()


class ReviewListAPIView(TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Review.objects.all().select_related("client", "computer", "session")

    def perform_create(self, serializer):
        # The client never supplies their own identity or club — derive them
        # server-side from the authenticated user and resolved tenant.
        club_id = getattr(self.request, "current_club_id", None) or self.request.data.get("club")
        serializer.save(client=self.request.user, club_id=club_id)


class ReviewMarkReadAPIView(TenantFilterMixin, generics.UpdateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Review.objects.all()

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_read = True
        obj.save(update_fields=["is_read"])
        return Response(self.get_serializer(obj).data)


class AdminCallListCreateAPIView(TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = AdminCallSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AdminCall.objects.all().select_related("computer", "client")

    def perform_create(self, serializer):
        # A client calling the operator is always themselves, in the current club.
        # computer may be supplied by the shell (it knows its own DB id) or left null.
        club_id = getattr(self.request, "current_club_id", None) or self.request.data.get("club")
        serializer.save(client=self.request.user, club_id=club_id)


class AdminCallAnswerAPIView(TenantFilterMixin, generics.UpdateAPIView):
    serializer_class = AdminCallSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AdminCall.objects.all()

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.answered_at:
            obj.answered_at = timezone.now()
            obj.answered_by = request.user
            obj.save(update_fields=["answered_at", "answered_by"])
        return Response(self.get_serializer(obj).data)
