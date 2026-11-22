from django.core.exceptions import ValidationError
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


class RouteType(models.TextChoices):
    BOULDER = "boulder", "Boulder"
    ROPED = "roped", "Roped"


class GradeSystem(models.TextChoices):
    EWBANK = "ewbank", "Ewbank"
    V = "v", "V"
    FONT = "font", "Font"
    FRENCH = "french", "French"


DEFAULT_GRADE_SYSTEM = {
    RouteType.BOULDER: GradeSystem.V,
    RouteType.ROPED: GradeSystem.EWBANK,
}


class Discipline(models.TextChoices):
    BOULDER = "boulder", "Boulder"
    TOP_ROPE = "top_rope", "Top-rope"
    SPORT = "sport", "Sport"


class Result(models.TextChoices):
    ONSIGHT = "onsight", "Onsight"
    FLASH = "flash", "Flash"
    SEND = "send", "Send"
    REPEAT = "repeat", "Repeat"
    DAB = "dab", "Dab"
    REDPOINT = "redpoint", "Redpoint"
    DOGGED = "dogged", "Dogged"
    RETREAT = "retreat", "Retreat"
    ATTEMPT = "attempt", "Attempt/working"


DISCIPLINES_BY_ROUTE_TYPE = {
    RouteType.BOULDER: [Discipline.BOULDER],
    RouteType.ROPED: [Discipline.TOP_ROPE, Discipline.SPORT],
}

RESULTS_BY_DISCIPLINE = {
    Discipline.BOULDER: [
        Result.ONSIGHT, Result.FLASH, Result.SEND, Result.REPEAT, Result.DAB,
        Result.ATTEMPT,
    ],
    Discipline.TOP_ROPE: [
        Result.ONSIGHT, Result.FLASH, Result.REPEAT, Result.DOGGED, Result.RETREAT,
        Result.ATTEMPT,
    ],
    Discipline.SPORT: [
        Result.ONSIGHT, Result.FLASH, Result.REDPOINT, Result.DOGGED, Result.RETREAT,
        Result.ATTEMPT,
    ],
}  # fmt: skip


class Route(models.Model):
    """A climb that can be attempted again. Indoor Routes are matched by name per location (reuse arrives in #42)."""

    name = models.CharField(max_length=200)
    grade = models.CharField(max_length=20, blank=True)
    grade_system = models.CharField(max_length=10, choices=GradeSystem, blank=True)
    route_type = models.CharField(max_length=10, choices=RouteType)
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.grade_system and self.route_type in DEFAULT_GRADE_SYSTEM:
            self.grade_system = DEFAULT_GRADE_SYSTEM[RouteType(self.route_type)]
        super().save(*args, **kwargs)


class Ascent(models.Model):
    """One attempt-or-completion of a Route during a Session."""

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="ascents"
    )
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="ascents")
    discipline = models.CharField(max_length=10, choices=Discipline)
    result = models.CharField(max_length=10, choices=Result)
    rests = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def clean(self) -> None:
        errors: dict[str, str] = {}
        if self.session.indoor_outdoor != Setting.INDOOR:
            errors["session"] = "Ascents can only be added to indoor Sessions."
        allowed = DISCIPLINES_BY_ROUTE_TYPE.get(RouteType(self.route.route_type), [])
        if self.discipline not in allowed:
            errors["discipline"] = (
                f"{self.get_discipline_display()} does not suit a "  # pyright: ignore[reportAttributeAccessIssue]
                f"{self.route.get_route_type_display().lower()} Route."  # pyright: ignore[reportAttributeAccessIssue]
            )
        elif self.result not in RESULTS_BY_DISCIPLINE[Discipline(self.discipline)]:
            errors["result"] = (
                f"{self.get_result_display()} is not a result for "  # pyright: ignore[reportAttributeAccessIssue]
                f"{self.get_discipline_display().lower()}."  # pyright: ignore[reportAttributeAccessIssue]
            )
        if self.result != Result.DOGGED:
            self.rests = None
        elif self.rests is not None and self.rests < 1:
            errors["rests"] = "Rests must be a positive whole number."
        if errors:
            raise ValidationError(errors)
