from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.api.v1.serializers import BookingSerializer
from apps.bookings.models import Booking, BookingStatus
from apps.clubs.api.v1.mixins import TenantFilterMixin, validated_club_id


class BookingListCreateAPIView(TenantFilterMixin, generics.ListCreateAPIView):
    """List + create bookings, scoped to the club the user is authorized for."""

    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Booking.objects.all().prefetch_related("hosts").select_related("client")
    pagination_class = None  # the Gantt/conflict-check needs ALL bookings, not page 1

    def get_queryset(self):
        qs = super().get_queryset()
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if from_date:
            qs = qs.filter(from_at__gte=from_date)
        if to_date:
            qs = qs.filter(to_at__lte=to_date)
        return qs.order_by("-from_at")

    def perform_create(self, serializer):
        # Tenant guard on WRITE: force the booking into the user's authorized club and
        # reject hosts (PCs) that aren't in it — don't trust club/hosts from the body.
        club_id = validated_club_id(self.request)
        if not club_id:
            raise PermissionDenied("Нет доступа к клубу")
        hosts = serializer.validated_data.get("hosts", [])
        for h in hosts:
            if getattr(h, "club_id", None) != club_id:
                raise ValidationError({"hosts": "ПК не принадлежит этому клубу"})

        # Reject time-overlapping bookings on the same PC (was no conflict check →
        # two operators could double-book the same slot).
        from_at = serializer.validated_data.get("from_at")
        to_at = serializer.validated_data.get("to_at")
        if from_at and to_at:
            if to_at <= from_at:
                raise ValidationError({"to_at": "Конец брони должен быть позже начала"})
            host_ids = [h.id for h in hosts]
            if host_ids:
                clash = (Booking.objects
                         .filter(club_id=club_id, status__in=[BookingStatus.ACTIVE, BookingStatus.REDEEMED],
                                 hosts__id__in=host_ids,
                                 from_at__lt=to_at, to_at__gt=from_at)
                         .exists())
                if clash:
                    raise ValidationError({"hosts": "На это время ПК уже забронирован"})
        serializer.save(created_by=self.request.user, club_id=club_id)


class BookingDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve/update/cancel a booking — tenant-scoped so foreign ids 404 (IDOR fix)."""

    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Booking.objects.all().prefetch_related("hosts")


class BookingRedeemAPIView(APIView):
    """Operator: "Клиент пришёл" — mark the PC's active booking REDEEMED so it isn't
    auto-cancelled as a no-show, and free the PC. Body: { computer_id, booking_id? }.
    (Was a dead frontend action with no endpoint, so bookings never reached REDEEMED.)"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.utils import timezone
        cid = validated_club_id(request)
        if not cid:
            return Response({"error": "Нет доступа к клубу"}, status=status.HTTP_403_FORBIDDEN)

        booking_id = request.data.get("booking_id")
        computer_id = request.data.get("computer_id") or request.data.get("computer")
        qs = Booking.objects.filter(club_id=cid, status=BookingStatus.ACTIVE)
        if booking_id:
            booking = qs.filter(pk=booking_id).first()
        elif computer_id:
            # The booking on this PC whose window is closest to now (started or imminent).
            now = timezone.now()
            booking = (qs.filter(hosts__id=computer_id, from_at__lte=now + timezone.timedelta(minutes=30))
                       .order_by("-from_at").first())
        else:
            return Response({"error": "Нужен computer_id или booking_id"}, status=status.HTTP_400_BAD_REQUEST)

        if not booking:
            return Response({"error": "Активная бронь не найдена"}, status=status.HTTP_404_NOT_FOUND)

        booking.status = BookingStatus.REDEEMED
        booking.save(update_fields=["status", "updated_at"])
        try:
            from apps.billing.services.audit import log_action
            from apps.billing.models import LogAction
            log_action(request, LogAction.DB_UPDATE, obj=booking, object_type="Booking",
                       club_id=cid, repr_=f"Бронь #{booking.id}: клиент пришёл",
                       payload={"booking": booking.id})
        except Exception:
            pass
        return Response({"success": True, "booking_id": booking.id, "status": booking.status})
