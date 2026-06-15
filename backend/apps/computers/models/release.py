from django.db import models
from django.utils.translation import gettext_lazy as _


class AppRelease(models.Model):
    version = models.CharField(_("Version"), max_length=50, unique=True)
    file = models.FileField(_("Installer File"), upload_to="updates/")
    description = models.TextField(_("Changelog"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("App Release")
        verbose_name_plural = _("App Releases")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Version {self.version} ({self.created_at.strftime('%Y-%m-%d')})"

    @property
    def download_url(self):
        if self.file:
            return self.file.url
        return ""
