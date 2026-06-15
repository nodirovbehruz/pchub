import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class USER_TYPES:
    """Simple class to hold user type constants for consistency"""

    OWNER = "owner"
    MANAGER = "manager"
    OPERATOR = "operator"
    ADMIN = "admin"
    USER = "user"

    CHOICES = [
        (OWNER, _("Владелец")),
        (MANAGER, _("Менеджер")),
        (OPERATOR, _("Оператор")),
        (ADMIN, _("Администратор")),
        (USER, _("Пользователь")),
    ]


class UserManager(BaseUserManager):
    """User Manager"""

    def create_user(
        self, username, email=None, phone=None, password=None, **extra_fields
    ):
        if not username:
            raise ValueError(_("The Username must be set for authentication."))

        if email:
            email = self.normalize_email(email)

        user = self.model(username=username, email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Creates and saves a SuperUser with the given username, email, and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        # Set user_type to 'admin' for superuser
        extra_fields.setdefault("user_type", USER_TYPES.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(
            username=username, email=email, password=password, **extra_fields
        )


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom User Model"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authentication
    username = models.CharField(
        _("Username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
    )
    email = models.EmailField(_("Email Address"), unique=True, null=True, blank=True)
    phone = PhoneNumberField(_("Phone Number"), unique=True, null=True, blank=True)

    # Profile & Role
    first_name = models.CharField(
        _("First Name"), max_length=150, null=True, blank=True
    )
    last_name = models.CharField(_("Last Name"), max_length=150, null=True, blank=True)
    date_of_birth = models.DateField(_("Date of Birth"), null=True, blank=True)
    profile_image = models.ImageField(
        _("Profile Image"), upload_to="profile_images/", null=True, blank=True
    )

    # User Type
    user_type = models.CharField(
        max_length=10, choices=USER_TYPES.CHOICES, default=USER_TYPES.USER
    )

    # Status Fields
    is_staff = models.BooleanField(_("Staff Status"), default=False)
    is_active = models.BooleanField(_("Is Active"), default=True)
    email_verified = models.BooleanField(_("Email Verified"), default=False)
    phone_verified = models.BooleanField(_("Phone Verified"), default=False)
    is_active_session = models.BooleanField(default=False)
    active_hardware_id = models.CharField(max_length=255, null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    # Location and Security
    region = models.CharField(_("Region"), max_length=100, blank=True, null=True)
    language = models.CharField(_("Language"), max_length=10, default="en")

    # Timestamps
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    last_login = models.DateTimeField(_("Last Login"), null=True, blank=True)

    objects = UserManager()

    # Django Authentication Configuration
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} | {self.get_user_type_display()}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.username

    @property
    def is_admin(self):
        """Check if user has an admin role (simplified from the first example)."""
        return self.user_type == USER_TYPES.ADMIN

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            try:
                from apps.billing.models import UserBalance

                UserBalance.objects.get_or_create(user=self)
            except ImportError:
                pass
