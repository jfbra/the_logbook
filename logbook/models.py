from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ActivityType(models.TextChoices):
    """Fixed, code-defined list. Only climbing is enabled for now."""

    CLIMBING = "climbing", "Climbing"


class Setting(models.TextChoices):
    INDOOR = "indoor", "Indoor"
    OUTDOOR = "outdoor", "Outdoor"


class Session(models.Model):
    """One bout of training on a given day. Ascents will attach to it later."""

    date = models.DateField()
    activity_type = models.CharField(max_length=20, choices=ActivityType)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    effort = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    location = models.CharField(max_length=200, blank=True)
    indoor_outdoor = models.CharField(max_length=10, choices=Setting, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self) -> str:
        return f"{self.date} {self.get_activity_type_display()}"  # pyright: ignore[reportAttributeAccessIssue]
