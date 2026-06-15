"""B2B club billing API: wallet (balance + history + top-up) and buying a
subscription plan from the wallet."""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clubs.models import Club, ClubMembership, SubscriptionPlan
from apps.clubs.services import billing as billing_service


def _is_platform_admin(user):
    return getattr(user, "is_admin", False) or getattr(user, "user_type", "") == "admin"


def _is_owner_or_admin(user, club):
    if _is_platform_admin(user):
        return True
    if club.owner_id == user.pk:
        return True
    return ClubMembership.objects.filter(
        user=user, club=club, is_active=True, role__in=["owner", "manager"]
    ).exists()


def _txn_row(t):
    return {
        "id": t.id, "type": t.type, "amount": str(t.amount),
        "balance_after": str(t.balance_after), "comment": t.comment,
        "by": getattr(t.created_by, "username", None), "created_at": t.created_at,
    }


class SubscriptionPlansAPIView(APIView):
    """GET /api/v1/subscription-plans/ — list of plans (Free/Starter/Business)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by("monthly_price")
        return Response([{
            "id": p.id, "tier": p.tier, "name": p.name,
            "monthly_price": str(p.monthly_price), "max_pcs": p.max_pcs,
            "features": p.features or {},
        } for p in plans])


class ClubWalletAPIView(APIView):
    """GET  /api/v1/clubs/<pk>/wallet/  — balance + recent transactions.
       POST /api/v1/clubs/<pk>/wallet/topup/  — super-admin credits the balance."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        if not _is_owner_or_admin(request.user, club):
            return Response({"error": "Нет доступа"}, status=status.HTTP_403_FORBIDDEN)
        wallet = billing_service.get_or_create_wallet(club)
        txns = wallet.transactions.select_related("created_by")[:50]
        return Response({
            "balance": str(wallet.balance),
            "pc_usage": billing_service.pc_usage(club.id),
            "transactions": [_txn_row(t) for t in txns],
        })


class ClubWalletTopupAPIView(APIView):
    """POST /api/v1/clubs/<pk>/wallet/topup/  {amount, comment} — SUPER-ADMIN only."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not _is_platform_admin(request.user):
            return Response({"error": "Только администратор платформы"}, status=status.HTTP_403_FORBIDDEN)
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        wallet = billing_service.topup(
            club, request.data.get("amount"), by_user=request.user,
            comment=request.data.get("comment", ""),
        )
        return Response({"success": True, "balance": str(wallet.balance)})


class ClubBuyPlanAPIView(APIView):
    """POST /api/v1/clubs/<pk>/subscription/buy/  {plan: id|tier} — owner buys/renews
    a plan, paying monthly_price from the wallet."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        if not _is_owner_or_admin(request.user, club):
            return Response({"error": "Нет доступа"}, status=status.HTTP_403_FORBIDDEN)

        plan = _resolve_plan(request.data.get("plan"))
        if not plan:
            return Response({"error": "Тариф не найден"}, status=status.HTTP_400_BAD_REQUEST)

        sub, wallet = billing_service.buy_plan(club, plan, by_user=request.user)
        return Response({
            "success": True,
            "plan": plan.name,
            "status": sub.status,
            "expires_at": sub.expires_at,
            "balance": str(wallet.balance),
        })


class ClubGrantSubscriptionAPIView(APIView):
    """POST /api/v1/clubs/<pk>/subscription/grant/  {plan, days} — SUPER-ADMIN grants
    a subscription WITHOUT charging the wallet."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not _is_platform_admin(request.user):
            return Response({"error": "Только администратор платформы"}, status=status.HTTP_403_FORBIDDEN)
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        plan = _resolve_plan(request.data.get("plan"))
        if not plan:
            return Response({"error": "Тариф не найден"}, status=status.HTTP_400_BAD_REQUEST)
        sub = billing_service.grant(club, plan, days=request.data.get("days", 30), by_user=request.user)
        return Response({"success": True, "plan": plan.name, "status": sub.status, "expires_at": sub.expires_at})


def _resolve_plan(value):
    if value is None:
        return None
    qs = SubscriptionPlan.objects.all()
    try:
        return qs.filter(id=int(value)).first()
    except (ValueError, TypeError):
        return qs.filter(tier=str(value)).first()
