from django.db import models
from django.utils.translation import gettext_lazy as _


class News(models.Model):
    """Club news, shown in Shell Home page (Business) and SmartGamer mobile app.

    Fields per SmartShell:
    - title 2..40 Unicode chars
    - body (truncated to 10 lines in mobile with «Показать полностью»)
    - optional button (text + URL)
    - is_published toggle
    - period (start/end dates)
    - cover image (min 312×176, opt 624×352, 16:9, ≤640 KB, .jpg/.png)
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="news",
    )

    title = models.CharField(max_length=40)
    body = models.TextField(blank=True, default="")

    button_text = models.CharField(max_length=40, blank=True, default="")
    button_url = models.URLField(blank=True, default="")

    cover_image = models.ImageField(
        upload_to="news/", blank=True, null=True,
        help_text=_("Min 312×176, opt 624×352, ratio 16:9, max 640 KB"),
    )

    is_published = models.BooleanField(default=False)
    show_from = models.DateTimeField(null=True, blank=True)
    show_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_news"
        verbose_name = _("News")
        verbose_name_plural = _("News")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "is_published", "-created_at"]),
        ]

    def __str__(self):
        return self.title
