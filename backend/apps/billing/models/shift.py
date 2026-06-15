from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Shift(models.Model):
    """
    Represents a work shift for a cashier/administrator.
    Required to perform financial operations.
    """
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="shifts",
        verbose_name=_("Club"),
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shifts",
        verbose_name=_("Administrator")
    )
    start_time = models.DateTimeField(default=timezone.now, verbose_name=_("Start Time"))
    end_time = models.DateTimeField(null=True, blank=True, verbose_name=_("End Time"))
    
    initial_cash = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, 
        verbose_name=_("Initial Cash")
    )
    closing_cash = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name=_("Closing Cash (Manual Entry)"),
        help_text=_("Amount of cash actually present in the register at the end of the shift.")
    )
    total_revenue_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue_card = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Total Revenue")
    )
    
    x_reports_generated = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    notes = models.TextField(blank=True, null=True, verbose_name=_("Notes"))

    class Meta:
        db_table = "billing_shifts"
        verbose_name = _("Shift")
        verbose_name_plural = _("Shifts")
        ordering = ["-start_time"]

    def __str__(self):
        end = self.end_time.strftime("%H:%M") if self.end_time else "..."
        return f"Shift {self.admin.username} ({self.start_time.strftime('%d.%m %H:%M')} - {end})"

    @classmethod
    def get_active_shift(cls):
        """Returns the currently active shift if any."""
        return cls.objects.filter(is_active=True).first()

    def close_shift(self, closing_cash):
        """Closes the current shift and calculates Z-Report totals."""
        from apps.billing.models.payment import Payment
        
        self.end_time = timezone.now()
        self.is_active = False
        self.closing_cash = closing_cash
        
        # Match the real-time calc (apps/billing/.../shifts.py:_shift_realtime):
        # scope by CLUB (not admin — multiple operators can ring sales in one shift)
        # and EXCLUDE refunds (a refund only stamps "[REFUNDED]" and keeps the
        # original positive amount_paid, which would otherwise inflate the Z-report).
        payments = Payment.objects.filter(created_at__gte=self.start_time).exclude(note__icontains="[REFUNDED]")
        if self.club_id:
            payments = payments.filter(club_id=self.club_id)
        else:
            payments = payments.filter(admin=self.admin)
        self.total_revenue_cash = sum(p.amount_paid for p in payments if p.payment_method == "cash")
        self.total_revenue_card = sum(p.amount_paid for p in payments if p.payment_method == "card")
        self.total_revenue = self.total_revenue_cash + self.total_revenue_card
        
        self.save()
        return self

    def _manual_cash_orders_net(self):
        """Net of MANUAL cash orders on this shift: ПКО (income) add to the drawer,
        РКО (outcome) remove. Auto-refund РКО ([AUTO-REFUND]) is excluded — that cash
        is already reflected by the refunded sale dropping out of total_revenue_cash,
        so counting it again would double-subtract."""
        from decimal import Decimal
        try:
            from django.db.models import Sum
            from apps.billing.models import CashOrder, CashOrderType
            orders = CashOrder.objects.filter(shift=self).exclude(comment__icontains="[AUTO-REFUND]")
            inc = orders.filter(type=CashOrderType.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
            out = orders.filter(type=CashOrderType.OUTCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
            return inc - out
        except Exception:
            return Decimal("0")

    @property
    def discrepancy(self):
        """Difference between expected cash and actual closing cash"""
        if self.closing_cash is None:
            return 0
        # Expected drawer = initial + cash revenue + manual ПКО − manual РКО.
        # CashOrders were ignored before → discrepancy was always off by any cash in/out.
        expected_cash = self.initial_cash + self.total_revenue_cash + self._manual_cash_orders_net()
        return self.closing_cash - expected_cash
