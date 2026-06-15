from django.db.models import TextChoices


class TransactionType(TextChoices):
    """Transaction types"""

    IN = "IN", "Stock In"
    OUT = "OUT", "Stock Out"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    SALE = "SALE", "Sale"
    RETURN = "RETURN", "Return"
    DAMAGED = "DAMAGED", "Damaged/Loss"
