from django.db import models
from django.utils.translation import gettext_lazy as _

class MapElement(models.Model):
    """Stores decorative and architectural elements on the club map (walls, furniture, etc.)"""
    
    ELEMENT_TYPES = (
        ('wall_h', 'Стена (горизонтальная)'),
        ('wall_v', 'Стена (вертикальная)'),
        ('door', 'Вход/Выход'),
        ('wc', 'Туалет'),
        ('bar', 'Бар'),
        ('reception', 'Ресепшн'),
        ('sofa', 'Диван'),
        ('fire', 'Огнетушитель'),
        ('billiard', 'Бильярд'),
        ('console', 'Консоль (PS/Xbox)'),
    )

    element_type = models.CharField(max_length=20, choices=ELEMENT_TYPES)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=40, help_text="Width in pixels")
    height = models.IntegerField(default=40, help_text="Height in pixels")
    rotation = models.IntegerField(default=0, help_text="Rotation in degrees")

    class Meta:
        db_table = "map_elements"
        verbose_name = _("Map Element")
        verbose_name_plural = _("Map Elements")

    def __str__(self):
        return f"{self.get_element_type_display()} at ({self.position_x}, {self.position_y})"
