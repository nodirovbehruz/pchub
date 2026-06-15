from rest_framework import serializers

from apps.loyalty.models import Achievement, CashbackRule, Discount, Promocode


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = "__all__"
        # club is read-only — set by TenantCreateMixin on create; a PATCH must not
        # re-assign an object to another tenant (mass-assignment / cross-club leak).
        read_only_fields = ["id", "club", "created_at", "updated_at"]


class PromocodeSerializer(serializers.ModelSerializer):
    is_exhausted = serializers.BooleanField(read_only=True)

    class Meta:
        model = Promocode
        fields = [
            "id", "club", "code", "name",
            "reward_type", "value",
            "client_group", "specific_clients",
            "applies_to_tariffs", "applies_to_products", "applies_to_services", "applies_to_combos",
            "channels",
            "usage_limit", "usage_count", "is_exhausted",
            "valid_from", "valid_until",
            "telegram_notify_on_use", "telegram_notify_on_expire",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "club", "usage_count", "is_exhausted", "created_at", "updated_at"]


class CashbackRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashbackRule
        fields = "__all__"
        read_only_fields = ["id", "club", "created_at", "updated_at"]


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = "__all__"
        read_only_fields = ["id", "club", "created_at"]
