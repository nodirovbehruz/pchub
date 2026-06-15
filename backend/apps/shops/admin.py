from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.shops.models import (
    Cart,
    CartItem,
    Category,
    Combo,
    ComboProductItem,
    ComboServiceItem,
    Order,
    OrderItem,
    Product,
    ProductGroup,
    ProductImage,
    ProductSet,
    ProductSetItem,
    ProductTag,
    Service,
    Stock,
    StockTransaction,
)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "price", "applies_discount", "is_active")
    list_filter = ("club", "is_active", "applies_discount")
    search_fields = ("name", "barcode")
    list_editable = ("is_active",)


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "schedule_start", "schedule_end", "show_in_shell", "is_active")
    list_filter = ("club", "is_active", "show_in_shell")
    search_fields = ("name",)


class ComboProductInline(admin.TabularInline):
    model = ComboProductItem
    extra = 0


class ComboServiceInline(admin.TabularInline):
    model = ComboServiceItem
    extra = 0


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "computer_group", "tariff", "sale_price", "is_active")
    list_filter = ("club", "is_active")
    search_fields = ("name",)
    inlines = [ComboProductInline, ComboServiceInline]

# ============================================================================
# INLINES
# ============================================================================


class ProductImageInline(admin.TabularInline):
    """Inline for product images"""

    model = ProductImage
    extra = 1
    fields = ("image", "image_preview", "order", "is_main")
    readonly_fields = ("image_preview",)
    ordering = ["order"]

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image and hasattr(obj.image, "url"):
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.image.url,
            )
        return "No Image"


class ProductSetItemInline(admin.TabularInline):
    """Inline for product set items"""

    model = ProductSetItem
    extra = 1
    fields = ("product", "quantity", "order", "subtotal_display")
    readonly_fields = ("subtotal_display",)
    autocomplete_fields = ["product"]
    ordering = ["order"]

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        if obj.product:
            return format_html("<strong>{}</strong>", obj.subtotal)
        return "-"


# ============================================================================
# CATEGORY ADMIN
# ============================================================================


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin with beautiful display"""

    list_display = [
        "name_display",
        "slug",
        "icon_display",
        "product_count_display",
        "order",
        "status_display",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["order"]
    ordering = ["order", "name"]
    date_hierarchy = "created_at"

    fieldsets = (
        (_("Basic Information"), {"fields": ("name", "slug", "description")}),
        (_("Display"), {"fields": ("icon", ("image", "image_preview"), "order")}),
        (_("Status"), {"fields": ("is_active",)}),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at", "image_preview"]

    @admin.display(description="Image Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                obj.image.url,
            )
        return "No Image"

    @admin.display(description="Name", ordering="name")
    def name_display(self, obj):
        """Display name with icon"""
        if obj.icon:
            return format_html(
                '<span style="font-size: 16px;">{} <strong>{}</strong></span>',
                obj.icon,
                obj.name,
            )
        return format_html("<strong>{}</strong>", obj.name)

    @admin.display(description="Icon")
    def icon_display(self, obj):
        """Display icon"""
        if obj.icon:
            return format_html('<span style="font-size: 24px;">{}</span>', obj.icon)
        return "-"

    @admin.display(description="Products", ordering="product_count")
    def product_count_display(self, obj):
        """Display product count with badge"""
        count = obj.product_count
        if count == 0:
            color = "#dc3545"  # Red
        elif count < 5:
            color = "#ffc107"  # Yellow
        else:
            color = "#28a745"  # Green

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-weight: bold; display: inline-block;">{}</span>',
            color,
            count,
        )

    @admin.display(description="Status", boolean=True, ordering="is_active")
    def status_display(self, obj):
        """Display status with colored indicator"""
        return obj.is_active

    actions = ["activate_categories", "deactivate_categories"]

    @admin.action(description="✅ Activate selected categories")
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} categories activated.")

    @admin.action(description="❌ Deactivate selected categories")
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} categories deactivated.")


# ============================================================================
# PRODUCT TAG ADMIN
# ============================================================================


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    """Product tag admin"""

    list_display = [
        "name_display",
        "slug",
        "color_preview",
        "product_count",
        "created_at",
    ]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]

    @admin.display(description="Tag Name")
    def name_display(self, obj):
        """Display tag name with color"""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; '
            'border-radius: 4px; font-weight: 500;">{}</span>',
            obj.color,
            obj.name,
        )

    @admin.display(description="Color")
    def color_preview(self, obj):
        """Display color preview"""
        return format_html(
            '<div style="width: 60px; height: 30px; background-color: {}; '
            'border: 2px solid #ddd; border-radius: 4px;"></div>'
            '<span style="margin-left: 10px; font-family: monospace;">{}</span>',
            obj.color,
            obj.color,
        )

    @admin.display(description="Products")
    def product_count(self, obj):
        """Count products with this tag"""
        count = obj.products.filter(is_active=True).count()
        return format_html(
            '<span style="color: #6c757d; font-weight: bold;">{}</span>', count
        )


# ============================================================================
# PRODUCT ADMIN
# ============================================================================


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Product admin with advanced features"""

    list_display = [
        "name_display",
        "category",
        "price_display",
        "stock_badge",
        "tags_display",
        "featured_badge",
        "status_badge",
        "order",
    ]
    list_filter = ["category", "is_active", "is_featured", "tags", "created_at"]
    search_fields = ["name", "slug", "description", "sku", "barcode"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["tags"]
    list_editable = ["order"]
    ordering = ["order", "name"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["category"]
    inlines = [ProductImageInline]

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "pos/",
                self.admin_site.admin_view(self.pos_view),
                name="shops_product_pos",
            ),
        ]
        return custom_urls + urls

    def pos_view(self, request):
        from django.shortcuts import render
        from django.http import JsonResponse
        import json
        from apps.shops.models import Category, Product, Order, OrderItem
        from apps.billing.models.shift import Shift
        from apps.billing.models.payment import Payment
        
        # SPRINT 5: Handle Checkout POST Action
        if request.method == "POST":
            # 1. We must have an active shift to receive money!
            shift = Shift.get_active_shift()
            if not shift:
                return JsonResponse({"status": "error", "message": "Смена не открыта! Зайдите в раздел Касса и начните новую смену."}, status=400)
            
            try:
                data = json.loads(request.body)
                items = data.get("items", [])
                payment_method = data.get("payment_method", "cash")
                
                if not items:
                    return JsonResponse({"status": "error", "message": "Корзина пуста"}, status=400)

                total_price = 0
                order_items_to_create = []
                
                # 2. Create the shell for the customer order (account allows null for guests)
                order = Order.objects.create(total_price=0, status="COMPLETED")
                
                # 3. Process items and calculate total precisely
                for item_data in items:
                    prod = Product.objects.get(id=item_data["id"])
                    qty = int(item_data["qty"])
                    price = prod.price
                    line_total = price * qty
                    total_price += line_total
                    
                    order_items_to_create.append(OrderItem(order=order, product=prod, quantity=qty, price=price))
                    
                # Store all items inside the order
                OrderItem.objects.bulk_create(order_items_to_create)
                order.total_price = total_price
                order.save()
                
                # 4. Generate the Payment record linking back to this order.
                # Since minutes_added defaults to 0 and Payment doesn't have a rigid type constraint,
                # we use note field to distinguish SHOP purchases.
                Payment.objects.create(
                    admin=request.user,
                    amount_paid=total_price,
                    minutes_added=0,
                    payment_method=payment_method,
                    note=f"[SHOP] Заказ #{order.id}"
                )
                
                return JsonResponse({"status": "success", "message": f"Оплата {total_price} сум прошла успешно! Заказ #{order.id} оформлен."})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=500)

        # GET request: Load the POS UI
        categories = Category.objects.filter(is_active=True)
        products = Product.objects.filter(is_active=True).select_related("category")
        
        context = dict(
            self.admin_site.each_context(request),
            categories=categories,
            products=products,
            title="Касса Магазина (POS)",
        )
        return render(request, "admin/shops/pos.html", context)

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("name", "slug", "description", "short_description")},
        ),
        (_("Classification"), {"fields": ("category", "tags")}),
        (
            _("Pricing"),
            {
                "fields": ("price", "original_price"),
                "description": "Set original_price to show discount",
            },
        ),
        (_("Media"), {"fields": (("main_image", "main_image_preview"),)}),
        (_("Status & Display"), {"fields": ("is_active", "is_featured", "order")}),
        (_("Metadata"), {"fields": ("sku", "barcode"), "classes": ("collapse",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at", "main_image_preview"]

    @admin.display(description="Image Preview")
    def main_image_preview(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.main_image.url,
            )
        return "No Image"

    @admin.display(description="Product", ordering="name")
    def name_display(self, obj):
        """Display product name with image thumbnail"""
        if obj.main_image:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 10px;">'
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">'
                "<strong>{}</strong>"
                "</div>",
                obj.main_image.url,
                obj.name,
            )
        return format_html("<strong>{}</strong>", obj.name)

    @admin.display(description="Price", ordering="price")
    def price_display(self, obj):
        """Display price with discount indicator"""
        if obj.has_discount:
            return format_html(
                '<div style="display: flex; flex-direction: column;">'
                '<span style="text-decoration: line-through; color: #999; font-size: 11px;">{}</span>'
                '<span style="color: #28a745; font-weight: bold; font-size: 14px;">{}</span>'
                '<span style="background-color: #28a745; color: white; padding: 2px 6px; '
                'border-radius: 3px; font-size: 10px; margin-top: 2px;">-{}%</span>'
                "</div>",
                obj.original_price,
                obj.price,
                obj.discount_percentage,
            )
        return format_html('<strong style="font-size: 14px;">{}</strong>', obj.price)

    @admin.display(description="Stock", ordering="stock__quantity")
    def stock_badge(self, obj):
        """Display stock with color coding"""
        stock_qty = obj.current_stock

        if stock_qty == 0:
            color = "#dc3545"  # Red
            icon = "❌"
            text = "OUT"
        elif stock_qty <= 10:
            color = "#ffc107"  # Yellow
            icon = "⚠️"
            text = f"{stock_qty} LOW"
        else:
            color = "#28a745"  # Green
            icon = "✅"
            text = str(stock_qty)

        return format_html(
            '<div style="display: flex; align-items: center; gap: 5px;">'
            "<span>{}</span>"
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-weight: bold; font-size: 12px;">{}</span>'
            "</div>",
            icon,
            color,
            text,
        )

    @admin.display(description="Tags")
    def tags_display(self, obj):
        """Display tags as colored badges"""
        tags = obj.tags.all()[:3]  # Show first 3 tags
        if not tags:
            return "-"

        badges = []
        for tag in tags:
            badges.append(
                f'<span style="background-color: {tag.color}; color: white; '
                f"padding: 3px 8px; border-radius: 3px; font-size: 11px; "
                f'margin-right: 4px;">{tag.name}</span>'
            )

        html = "".join(badges)

        # Add "+X more" if there are more tags
        remaining = obj.tags.count() - 3
        if remaining > 0:
            html += f'<span style="color: #6c757d; font-size: 11px;">+{remaining} more</span>'

        return format_html(html)

    @admin.display(description="Featured", boolean=True, ordering="is_featured")
    def featured_badge(self, obj):
        """Display featured status"""
        return obj.is_featured

    @admin.display(description="Active", boolean=True, ordering="is_active")
    def status_badge(self, obj):
        """Display active status"""
        return obj.is_active

    actions = [
        "mark_featured",
        "unmark_featured",
        "activate_products",
        "deactivate_products",
    ]

    @admin.action(description="⭐ Mark as featured")
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} products marked as featured.")

    @admin.action(description="Remove featured status")
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} products unmarked from featured.")

    @admin.action(description="✅ Activate selected products")
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} products activated.")

    @admin.action(description="❌ Deactivate selected products")
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} products deactivated.")


# ============================================================================
# PRODUCT SET ADMIN
# ============================================================================


@admin.register(ProductSet)
class ProductSetAdmin(admin.ModelAdmin):
    """Product set admin with bundle display"""

    list_display = [
        "name_display",
        "price_display",
        "items_count",
        "savings_display",
        "featured_badge",
        "status_badge",
        "order",
    ]
    list_filter = ["is_active", "is_featured", "created_at"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["order"]
    ordering = ["order", "name"]
    inlines = [ProductSetItemInline]

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("name", "slug", "description", "short_description")},
        ),
        (
            _("Pricing"),
            {
                "fields": ("price", "original_price"),
                "description": "Original price shows total if items bought separately",
            },
        ),
        (_("Media"), {"fields": ("main_image",)}),
        (_("Status & Display"), {"fields": ("is_active", "is_featured", "order")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Set Name", ordering="name")
    def name_display(self, obj):
        """Display set name with icon"""
        return format_html(
            '<span style="font-size: 14px;">📦 <strong>{}</strong></span>', obj.name
        )

    @admin.display(description="Price", ordering="price")
    def price_display(self, obj):
        """Display bundle price"""
        if obj.original_price:
            return format_html(
                '<div style="display: flex; flex-direction: column;">'
                '<span style="text-decoration: line-through; color: #999; font-size: 11px;">{}</span>'
                '<span style="color: #28a745; font-weight: bold; font-size: 14px;">{}</span>'
                "</div>",
                obj.original_price,
                obj.price,
            )
        return format_html("<strong>{}</strong>", obj.price)

    @admin.display(description="Items")
    def items_count(self, obj):
        """Display total items in set"""
        total = obj.total_items
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-weight: bold;">{} items</span>',
            total,
        )

    @admin.display(description="Savings", ordering="price")
    def savings_display(self, obj):
        """Display savings amount and percentage"""
        if obj.savings > 0:
            return format_html(
                '<div style="display: flex; flex-direction: column; align-items: flex-start;">'
                '<span style="color: #28a745; font-weight: bold;">-{}</span>'
                '<span style="background-color: #28a745; color: white; padding: 2px 6px; '
                'border-radius: 3px; font-size: 10px;">{}% OFF</span>'
                "</div>",
                obj.savings,
                obj.savings_percentage,
            )
        return "-"

    @admin.display(description="Featured", boolean=True, ordering="is_featured")
    def featured_badge(self, obj):
        """Display featured status"""
        return obj.is_featured

    @admin.display(description="Active", boolean=True, ordering="is_active")
    def status_badge(self, obj):
        """Display active status"""
        return obj.is_active

    actions = ["auto_calculate_original_price", "mark_featured", "unmark_featured"]

    @admin.action(description="🧮 Auto-calculate original price")
    def auto_calculate_original_price(self, request, queryset):
        updated = 0
        for product_set in queryset:
            original_price = product_set.calculate_original_price()
            product_set.original_price = original_price
            product_set.save()
            updated += 1
        self.message_user(request, f"Original price calculated for {updated} sets.")

    @admin.action(description="⭐ Mark as featured")
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} sets marked as featured.")

    @admin.action(description="Remove featured status")
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} sets unmarked from featured.")


# ============================================================================
# STOCK ADMIN
# ============================================================================


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Stock management admin"""

    list_display = [
        "product_display",
        "quantity_badge",
        "reserved_quantity",
        "available_badge",
        "status_badge",
        "threshold",
        "updated_at",
    ]
    list_filter = ["updated_at"]
    search_fields = ["product__name", "product__sku"]
    autocomplete_fields = ["product"]
    readonly_fields = ["updated_at"]

    fieldsets = (
        (_("Product"), {"fields": ("product",)}),
        (
            _("Stock Levels"),
            {"fields": ("quantity", "reserved_quantity", "low_stock_threshold")},
        ),
        (_("Info"), {"fields": ("updated_at",)}),
    )

    @admin.display(description="Product", ordering="product__name")
    def product_display(self, obj):
        """Display product name"""
        return format_html("<strong>{}</strong>", obj.product.name)

    @admin.display(description="Quantity", ordering="quantity")
    def quantity_badge(self, obj):
        """Display quantity with color coding"""
        if obj.is_out_of_stock:
            color = "#dc3545"
            icon = "❌"
        elif obj.is_low_stock:
            color = "#ffc107"
            icon = "⚠️"
        else:
            color = "#28a745"
            icon = "✅"

        return format_html(
            '<div style="display: flex; align-items: center; gap: 5px;">'
            "<span>{}</span>"
            '<span style="background-color: {}; color: white; padding: 5px 12px; '
            'border-radius: 12px; font-weight: bold; font-size: 14px;">{}</span>'
            "</div>",
            icon,
            color,
            obj.quantity,
        )

    @admin.display(description="Available", ordering="quantity")
    def available_badge(self, obj):
        """Display available quantity"""
        available = obj.available_quantity
        return format_html(
            '<span style="color: #007bff; font-weight: bold; font-size: 14px;">{}</span>',
            available,
        )

    @admin.display(description="Status")
    def status_badge(self, obj):
        """Display stock status"""
        if obj.is_out_of_stock:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 5px 10px; '
                'border-radius: 4px; font-weight: bold;">OUT OF STOCK</span>'
            )
        elif obj.is_low_stock:
            return format_html(
                '<span style="background-color: #ffc107; color: #000; padding: 5px 10px; '
                'border-radius: 4px; font-weight: bold;">LOW STOCK</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 5px 10px; '
            'border-radius: 4px; font-weight: bold;">IN STOCK</span>'
        )

    @admin.display(description="Threshold", ordering="low_stock_threshold")
    def threshold(self, obj):
        """Display low stock threshold"""
        return obj.low_stock_threshold

    actions = ["add_stock_10", "add_stock_50", "add_stock_100", "reset_reserved"]

    @admin.action(description="➕ Add 10 to stock")
    def add_stock_10(self, request, queryset):
        for stock in queryset:
            stock.add_stock(10, "Bulk add from admin", request.user)
        self.message_user(request, f"Added 10 items to {queryset.count()} stock(s).")

    @admin.action(description="➕ Add 50 to stock")
    def add_stock_50(self, request, queryset):
        for stock in queryset:
            stock.add_stock(50, "Bulk add from admin", request.user)
        self.message_user(request, f"Added 50 items to {queryset.count()} stock(s).")

    @admin.action(description="➕ Add 100 to stock")
    def add_stock_100(self, request, queryset):
        for stock in queryset:
            stock.add_stock(100, "Bulk add from admin", request.user)
        self.message_user(request, f"Added 100 items to {queryset.count()} stock(s).")

    @admin.action(description="🔄 Reset reserved quantity")
    def reset_reserved(self, request, queryset):
        updated = queryset.update(reserved_quantity=0)
        self.message_user(request, f"Reset reserved quantity for {updated} stock(s).")


# ============================================================================
# STOCK TRANSACTION ADMIN
# ============================================================================


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    """Stock transaction history admin"""

    list_display = [
        "created_at",
        "product_name",
        "transaction_type_badge",
        "quantity_change",
        "quantity_before",
        "quantity_after",
        "user_display",
        "reason_short",
    ]
    list_filter = ["transaction_type", "created_at"]
    search_fields = ["stock__product__name", "reason", "reference_id"]
    readonly_fields = [
        "stock",
        "transaction_type",
        "quantity",
        "quantity_before",
        "quantity_after",
        "reason",
        "reference_id",
        "user",
        "created_at",
    ]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            _("Transaction Details"),
            {"fields": ("stock", "transaction_type", "quantity")},
        ),
        (_("Stock Levels"), {"fields": ("quantity_before", "quantity_after")}),
        (
            _("Additional Info"),
            {"fields": ("reason", "reference_id", "user", "created_at")},
        ),
    )

    def has_add_permission(self, request):
        """Disable manual creation"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make read-only"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deletion"""
        return False

    @admin.display(description="Product", ordering="stock__product__name")
    def product_name(self, obj):
        """Display product name"""
        return obj.stock.product.name

    @admin.display(description="Type", ordering="transaction_type")
    def transaction_type_badge(self, obj):
        """Display transaction type with color"""
        type_colors = {
            "IN": "#28a745",  # Green
            "OUT": "#dc3545",  # Red
            "ADJUSTMENT": "#007bff",  # Blue
            "SALE": "#fd7e14",  # Orange
            "RETURN": "#17a2b8",  # Cyan
            "DAMAGED": "#6c757d",  # Gray
        }

        color = type_colors.get(obj.transaction_type, "#6c757d")

        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; '
            'border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_transaction_type_display(),
        )

    @admin.display(description="Change", ordering="quantity")
    def quantity_change(self, obj):
        """Display quantity change with sign"""
        if obj.transaction_type in ["OUT", "SALE", "DAMAGED"]:
            color = "#dc3545"
            sign = "-"
        else:
            color = "#28a745"
            sign = "+"

        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 14px;">{}{}</span>',
            color,
            sign,
            obj.quantity,
        )

    @admin.display(description="User", ordering="user__username")
    def user_display(self, obj):
        """Display user who made the transaction"""
        if obj.user:
            return format_html(
                '<span style="color: #6c757d;">👤 {}</span>', obj.user.username
            )
        return "-"

    @admin.display(description="Reason")
    def reason_short(self, obj):
        """Display shortened reason"""
        if obj.reason:
            return obj.reason[:50] + ("..." if len(obj.reason) > 50 else "")
        return "-"


# ============================================================================
# CART ADMIN
# ============================================================================


class CartItemInline(admin.TabularInline):
    """Inline for cart items"""

    model = CartItem
    extra = 0
    fields = ("product", "quantity", "subtotal_display")
    readonly_fields = ("subtotal_display",)
    autocomplete_fields = ["product"]

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        if obj.product:
            return format_html("<strong>{}</strong>", obj.subtotal)
        return "-"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Shopping cart admin"""

    list_display = [
        "account_display",
        "items_count",
        "total_display",
        "updated_at",
    ]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["account__username", "account__email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CartItemInline]

    fieldsets = (
        (_("Cart Information"), {"fields": ("account",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Account", ordering="account__username")
    def account_display(self, obj):
        return format_html(
            '<span style="color: #007bff; font-weight: 500;">👤 {}</span>',
            obj.account.username,
        )

    @admin.display(description="Items")
    def items_count(self, obj):
        count = obj.total_items
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            count,
        )

    @admin.display(description="Total", ordering="id")
    def total_display(self, obj):
        return format_html(
            '<strong style="color: #28a745; font-size: 14px;">{}</strong>',
            obj.total_price,
        )


# ============================================================================
# ORDER ADMIN
# ============================================================================


class OrderItemInline(admin.TabularInline):
    """Inline for order items"""

    model = OrderItem
    extra = 0
    fields = ("product", "quantity", "price", "subtotal_display")
    readonly_fields = ("subtotal_display",)
    autocomplete_fields = ["product"]

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        if obj.product:
            return format_html("<strong>{}</strong>", obj.subtotal)
        return "-"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order management admin"""

    list_display = [
        "order_number",
        "account_display",
        "computer_display",
        "status_badge",
        "items_count",
        "total_price",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "account__username", "account__email"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]

    fieldsets = (
        (_("Order Information"), {"fields": ("account", "computer", "status")}),
        (_("Pricing"), {"fields": ("total_price",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Order #", ordering="id")
    def order_number(self, obj):
        return format_html("<strong>#{}</strong>", obj.id)

    @admin.display(description="Customer", ordering="account__username")
    def account_display(self, obj):
        return format_html(
            '<span style="color: #007bff; font-weight: 500;">👤 {}</span>',
            obj.account.username,
        )

    @admin.display(description="Computer", ordering="computer")
    def computer_display(self, obj):
        if obj.computer:
            return format_html(
                '<span style="color: #6f42c1; font-weight: 500;">🖥️ PC #{} ({})</span>',
                obj.computer.pc_number or "?",
                obj.computer.name,
            )
        return "-"

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        status_config = {
            "PENDING": {"color": "#ffc107", "bg": "#fff3cd"},
            "PROCESSING": {"color": "#17a2b8", "bg": "#d1ecf1"},
            "COMPLETED": {"color": "#28a745", "bg": "#d4edda"},
            "CANCELLED": {"color": "#dc3545", "bg": "#f8d7da"},
        }
        config = status_config.get(obj.status, {"color": "#6c757d", "bg": "#e2e3e5"})
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 5px 12px; '
            'border-radius: 14px; font-weight: bold; font-size: 11px;">{}</span>',
            config["bg"],
            config["color"],
            obj.get_status_display().upper(),
        )

    @admin.display(description="Items")
    def items_count(self, obj):
        count = obj.items.count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            count,
        )

    actions = [
        "mark_processing",
        "mark_completed",
        "mark_cancelled",
    ]

    @admin.action(description="📦 Mark as Processing")
    def mark_processing(self, request, queryset):
        updated = queryset.update(status="PROCESSING")
        self.message_user(request, f"{updated} order(s) marked as processing.")

    @admin.action(description="✅ Mark as Completed")
    def mark_completed(self, request, queryset):
        updated = queryset.update(status="COMPLETED")
        self.message_user(request, f"{updated} order(s) marked as completed.")

    @admin.action(description="❌ Mark as Cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status="CANCELLED")
        self.message_user(request, f"{updated} order(s) cancelled.")


# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================

# Customize admin site header and title
admin.site.site_header = "🛒 PCHub Shop Administration"
admin.site.site_title = "PCHub Shop Admin"
admin.site.index_title = "Shop Management Dashboard"
