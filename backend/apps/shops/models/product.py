"""Games products"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ProductTag(models.Model):
    """Product tags"""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    color = models.CharField(
        max_length=7, default="#6c757d", help_text="Hex color code"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shop_product_tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """Individual products"""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=255, blank=True)

    category = models.ForeignKey(
        "shops.Category", on_delete=models.CASCADE, related_name="products"
    )
    tags = models.ManyToManyField(ProductTag, related_name="products", blank=True)

    # Pricing
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Purchase price for stock valuation",
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Original price for showing discounts in shell",
    )

    # Images
    main_image = models.ImageField(upload_to="products/", blank=True, null=True)

    # Tenant + soft group
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="products",
        help_text="Club this product belongs to (tenant isolation)",
    )
    product_group = models.ForeignKey(
        "shops.ProductGroup",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="products",
        help_text="Product group with schedule (separate from Category)",
    )

    # Status
    is_active = models.BooleanField(default=True)
    shell_display = models.BooleanField(default=True, help_text="Show in client shell")
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")

    # Pricing/discount flags
    applies_discount = models.BooleanField(
        default=True,
        help_text="Whether club/client discounts apply to this product",
    )

    # Fiscal/RU compliance
    is_excise = models.BooleanField(
        default=False,
        help_text="Подакцизный товар — special fiscal flag for alcohol/tobacco",
    )
    honest_sign = models.BooleanField(
        default=False,
        help_text="Честный знак (CRPT) marking required — sale needs Data Matrix scan",
    )
    tax_rate = models.CharField(
        max_length=20, default="vat0",
        help_text="Tax rate code (vat0, vat10, vat20, etc.)",
    )
    notify_low_stock = models.BooleanField(
        default=False,
        help_text="Send Telegram alert when stock falls below threshold",
    )

    # Metadata
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # Ordering
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shop_products"
        ordering = ["order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return self.name

    @property
    def has_discount(self):
        """Check if product has discount"""
        return self.original_price and self.original_price > self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.has_discount:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0

    @property
    def current_stock(self):
        """Get current stock quantity"""
        try:
            return self.stock.quantity
        except:
            return 0

    @property
    def in_stock(self):
        """Check if product is in stock"""
        return self.current_stock > 0


class ProductImage(models.Model):
    """Additional product images"""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_main = models.BooleanField(default=False)

    class Meta:
        db_table = "shop_product_images"
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.product.name}"
