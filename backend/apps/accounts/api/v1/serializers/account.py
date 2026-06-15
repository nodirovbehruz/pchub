from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from apps.accounts.models import CustomUser


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    phone = PhoneNumberField()

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone",
        ]

    def validate_username(self, value):
        """Check if username already exists"""
        if CustomUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate_email(self, value):
        """Check if email already exists"""
        if value and CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone(self, value):
        """Check if phone number already exists"""
        if value and CustomUser.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    hardware_id = serializers.CharField(required=False, allow_null=True)

    # Response fields
    refresh = serializers.CharField(read_only=True)
    access = serializers.CharField(read_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""

    wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "phone",
            "date_of_birth",
            "profile_image",
            "is_active_session",
            "wallet_balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "user_type",
            "wallet_balance",
            "is_active_session",
            "created_at",
            "updated_at",
        ]

    def get_wallet_balance(self, obj):
        return 0


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users (admin view)"""

    wallet_balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "is_active",
            "is_active_session",
            "wallet_balance",
            "created_at",
        ]
