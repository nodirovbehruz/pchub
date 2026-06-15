from rest_framework import serializers

from apps.billing.models import PaymentMethod, TariffPlan, TariffPrice


class TopUpSerializer(serializers.Serializer):
    user_id = serializers.CharField()  # UUID string
    minutes = serializers.IntegerField(min_value=0, max_value=1440, default=0)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    payment_method = serializers.ChoiceField(
        choices=[PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.TRANSFER],
        default=PaymentMethod.CASH,
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class BalanceResponseSerializer(serializers.Serializer):
    has_access = serializers.BooleanField()
    minutes_remaining = serializers.IntegerField()
    formatted_time = serializers.CharField()


class TariffPriceSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = TariffPrice
        fields = ["id", "group", "group_name", "period", "price"]


class TariffPlanSerializer(serializers.ModelSerializer):
    hours_display = serializers.CharField(read_only=True)
    days_label = serializers.CharField(read_only=True)
    prices = TariffPriceSerializer(many=True, required=False)

    class Meta:
        model = TariffPlan
        fields = [
            "id", "club",
            "name", "tariff_type",
            "price", "minutes",
            "valid_until_time", "life_days",
            "schedule_days", "schedule_start", "schedule_end",
            "is_night", "apply_discount", "has_schedule",
            "is_active",
            "created_at", "updated_at",
            "hours_display", "days_label",
            "prices",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "hours_display", "days_label"]

    def create(self, validated_data):
        prices_data = validated_data.pop("prices", [])
        tariff = TariffPlan.objects.create(**validated_data)
        for p in prices_data:
            TariffPrice.objects.create(tariff=tariff, **p)
        return tariff

    def update(self, instance, validated_data):
        prices_data = validated_data.pop("prices", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if prices_data is not None:
            instance.prices.all().delete()
            for p in prices_data:
                TariffPrice.objects.create(tariff=instance, **p)
        return instance


class TariffPlanCreateSerializer(serializers.Serializer):
    """Legacy compatibility serializer (kept for existing endpoint)."""
    name = serializers.CharField(max_length=100)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    minutes = serializers.IntegerField(min_value=1, max_value=10080)  # up to 7 days
