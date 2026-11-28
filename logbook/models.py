import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models, transaction
from django.db.models.functions import Lower

from .grades import GRADES_BY_SYSTEM


class ActivityType(models.TextChoices):
    """Fixed, code-defined list. No field uses it until Activities are recorded."""

    CLIMBING = "climbing", "Climbing"
    HIKING = "hiking", "Hiking"
    MOUNTAINEERING = "mountaineering", "Mountaineering"
    RUNNING = "running", "Running"
    WALKING = "walking", "Walking"


class Session(models.Model):
    """One bout of training over one or more days, made of what is recorded on it."""

    date = models.DateField("start date")
    end_date = models.DateField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    effort = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self) -> str:
        if self.end_date and self.end_date != self.date:
            return f"{self.date} to {self.end_date}"
        return str(self.date)

    @property
    def last_date(self) -> datetime.date:
        return self.end_date or self.date

    @property
    def gyms(self) -> list["Gym"]:
        """The distinct Gyms of this Session's Ascents, by name.

        Prefetch `ascents__route__gym` before reading this for many Sessions.
        """
        gyms = {a.route.gym for a in self.ascents.all()}  # pyright: ignore[reportAttributeAccessIssue]
        return sorted(gyms, key=lambda gym: gym.name.lower())

    def clean(self) -> None:
        if self.date is None:
            return  # The field's own "required" error covers this.
        if self.end_date and self.end_date < self.date:
            raise ValidationError(
                {"end_date": "The end date cannot be before the start date."}
            )
        if self.pk:
            outside = self.ascents.exclude(  # pyright: ignore[reportAttributeAccessIssue]
                date__range=(self.date, self.last_date)
            ).count()
            if outside:
                raise ValidationError(
                    f"{outside} Ascent{'s' if outside != 1 else ''} would fall "
                    "outside these dates. Change or delete them first."
                )


class GymManager(models.Manager["Gym"]):
    def named(self, name: str) -> "Gym":
        """The Gym with this name (ignoring case), created if it does not exist."""
        name = name.strip()
        existing = self.filter(name__iexact=name).first()
        if existing:
            return existing
        try:
            with transaction.atomic():
                return self.create(name=name)
        except IntegrityError:
            # A concurrent request created it first.
            return self.get(name__iexact=name)


class Gym(models.Model):
    """A climbing gym. Created by name alone; the rest is filled in later."""

    objects = GymManager()

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    class Meta:
        ordering = [Lower("name"), "id"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="gym_name_unique_ignoring_case")
        ]

    def __str__(self) -> str:
        return self.name


class RouteType(models.TextChoices):
    TOP_ROPE = "top_rope", "Top-rope"
    SPORT = "sport", "Sport"
    BOULDER = "boulder", "Boulder"


INDOOR_ROUTE_TYPES = [RouteType.TOP_ROPE, RouteType.SPORT, RouteType.BOULDER]
INDOOR_ROUTE_TYPE_CHOICES = [(t.value, t.label) for t in INDOOR_ROUTE_TYPES]


class GradeSystem(models.TextChoices):
    EWBANK = "ewbank", "Ewbank"
    V = "v", "V"
    FONT = "font", "Font"
    FRENCH = "french", "French"


DEFAULT_GRADE_SYSTEM = {
    RouteType.BOULDER: GradeSystem.V,
    RouteType.TOP_ROPE: GradeSystem.EWBANK,
    RouteType.SPORT: GradeSystem.EWBANK,
}


class Discipline(models.TextChoices):
    BOULDER = "boulder", "Boulder"
    TOP_ROPE = "top_rope", "Top-rope"
    SPORT = "sport", "Sport"


class Result(models.TextChoices):
    ONSIGHT = "onsight", "Onsight"
    FLASH = "flash", "Flash"
    REDPOINT = "redpoint", "Redpoint"
    DOGGED = "dogged", "Dogged"
    WORKING = "working", "Working"
    ATTEMPT = "attempt", "Attempt"
    DAB = "dab", "Dab"
    REPEAT = "repeat", "Repeat"
    TICK = "tick", "Tick"


DISCIPLINES_BY_ROUTE_TYPE = {
    RouteType.BOULDER: [Discipline.BOULDER],
    RouteType.TOP_ROPE: [Discipline.TOP_ROPE],
    RouteType.SPORT: [Discipline.SPORT, Discipline.TOP_ROPE],
}

RESULTS_BY_DISCIPLINE = {
    Discipline.BOULDER: [
        Result.ONSIGHT, Result.FLASH, Result.WORKING, Result.ATTEMPT, Result.DAB,
        Result.TICK, Result.REPEAT,
    ],
    Discipline.TOP_ROPE: [
        Result.ONSIGHT, Result.FLASH, Result.DOGGED, Result.WORKING, Result.ATTEMPT,
        Result.TICK,
    ],
    Discipline.SPORT: [
        Result.ONSIGHT, Result.FLASH, Result.REDPOINT, Result.DOGGED, Result.WORKING,
        Result.ATTEMPT, Result.TICK,
    ],
}  # fmt: skip


class Route(models.Model):
    """Shared fields and rules of a climb that can be attempted again (abstract)."""

    name = models.CharField(max_length=200)
    grade = models.CharField(max_length=20, blank=True)
    grade_system = models.CharField(max_length=10, choices=GradeSystem, blank=True)
    route_type = models.CharField(max_length=10, choices=RouteType)
    stars = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    length_m = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    description = models.TextField(blank=True)
    style = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.apply_default_grade_system()
        super().save(*args, **kwargs)

    def apply_default_grade_system(self) -> None:
        if not self.grade_system and self.route_type in DEFAULT_GRADE_SYSTEM:
            self.grade_system = DEFAULT_GRADE_SYSTEM[RouteType(self.route_type)]

    def clean(self) -> None:
        self.apply_default_grade_system()
        if not self.grade:
            raise ValidationError({"grade": "A grade is required."})
        if self.grade not in GRADES_BY_SYSTEM.get(self.grade_system, []):
            raise ValidationError(
                {
                    "grade": f"{self.grade} is not a "
                    f"{self.get_grade_system_display()} grade."  # pyright: ignore[reportAttributeAccessIssue]
                }
            )


class IndoorRoute(Route):
    """A Route at a Gym. Names repeat after resets, so they are not unique."""

    route_type = models.CharField(max_length=10, choices=INDOOR_ROUTE_TYPE_CHOICES)
    gym = models.ForeignKey(Gym, on_delete=models.PROTECT, related_name="routes")
    setter = models.CharField(max_length=100, blank=True)
    hold_colour = models.CharField(max_length=50, blank=True)
    date_set = models.DateField(null=True, blank=True)
    rope_number = models.CharField(max_length=20, blank=True)
    bolts = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    area = models.CharField(max_length=100, blank=True)

    def clean(self) -> None:
        errors: dict[str, str | list[str]] = {}
        try:
            super().clean()
        except ValidationError as error:
            errors.update(error.message_dict)
        kind = RouteType(self.route_type) if self.route_type else None
        if self.rope_number and kind == RouteType.BOULDER:
            errors["rope_number"] = "A boulder has no rope number."
        if self.bolts is not None and kind != RouteType.SPORT:
            errors["bolts"] = "Bolts only apply to sport Routes."
        if self.area and kind != RouteType.BOULDER:
            errors["area"] = "Area only applies to boulders."
        if errors:
            raise ValidationError(errors)


class Ascent(models.Model):
    """Shared fields and rules of one attempt-or-completion of a Route (abstract).

    Concrete subclasses add `session` and `route`.
    """

    # Blank means "the Session's start date": see `clean_date`.
    date = models.DateField(blank=True)
    discipline = models.CharField(max_length=10, choices=Discipline)
    result = models.CharField(max_length=10, choices=Result)
    rests = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["date", "created_at", "id"]

    def clean_date(self, session: Session) -> dict[str, str]:
        """Default the date to the Session's start; it must lie within its dates."""
        if self.date is None:
            self.date = session.date
        if not session.date <= self.date <= session.last_date:
            return {"date": f"The date must be within the Session ({session})."}
        return {}

    def clean_discipline_result_rests(self, route: Route) -> dict[str, str]:
        errors: dict[str, str] = {}
        allowed = DISCIPLINES_BY_ROUTE_TYPE.get(RouteType(route.route_type), [])
        if self.discipline not in allowed:
            errors["discipline"] = (
                f"{self.get_discipline_display()} does not suit a "  # pyright: ignore[reportAttributeAccessIssue]
                f"{route.get_route_type_display().lower()} Route."  # pyright: ignore[reportAttributeAccessIssue]
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
        return errors


class IndoorAscent(Ascent):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="ascents"
    )
    route = models.ForeignKey(
        IndoorRoute, on_delete=models.PROTECT, related_name="ascents"
    )

    class Meta(Ascent.Meta):
        abstract = False

    def save(self, *args, **kwargs):
        if self.date is None:
            self.date = self.session.date
        super().save(*args, **kwargs)

    def clean(self) -> None:
        errors = self.clean_date(self.session)
        errors.update(self.clean_discipline_result_rests(self.route))
        if errors:
            raise ValidationError(errors)
