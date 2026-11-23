from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .grades import GRADES_BY_SYSTEM
from .models import (
    DEFAULT_GRADE_SYSTEM,
    DISCIPLINES_BY_ROUTE_TYPE,
    Discipline,
    GradeSystem,
    Gym,
    INDOOR_ROUTE_TYPE_CHOICES,
    IndoorAscent,
    IndoorRoute,
    RESULTS_BY_DISCIPLINE,
    Result,
    RouteType,
    Session,
)


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            "date",
            "activity_type",
            "duration_minutes",
            "effort",
            "location",
            "indoor_outdoor",
            "notes",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate
        self.fields["activity_type"].initial = "climbing"

    def clean_indoor_outdoor(self) -> str:
        setting = self.cleaned_data["indoor_outdoor"]
        count = self.instance.ascents.count() if self.instance.pk else 0  # pyright: ignore[reportAttributeAccessIssue]
        if count and setting != self.instance.indoor_outdoor:
            raise ValidationError(
                f"The setting cannot be changed because this Session has {count} "
                f"Ascent{'s' if count != 1 else ''}. Delete them first."
            )
        return setting


def grade_choices(
    route_type: str = "", grade_system: str = ""
) -> list[tuple[str, str]]:
    """Grades for the chosen system, or the type's default system, else V."""
    system = grade_system or DEFAULT_GRADE_SYSTEM.get(route_type, GradeSystem.V)  # pyright: ignore[reportArgumentType, reportCallIssue]
    grades = GRADES_BY_SYSTEM.get(str(system), [])
    return [("", "---------"), *((g, g) for g in grades)]


def result_choices(discipline: str = "") -> list[tuple[str, str]]:
    """The Results that suit a Discipline (none for an unknown one)."""
    try:
        allowed = RESULTS_BY_DISCIPLINE[Discipline(discipline)]
    except ValueError:
        return []
    return [(r.value, str(r.label)) for r in allowed]


def narrow_results(form: forms.BaseForm, discipline: str) -> None:
    """Offer only the Results for the Discipline, and re-fetch them when it changes.

    Only the rendered options are narrowed; validation still sees every Result so
    that a mismatch gets the model's explanatory error.
    """
    choices = dict(form.fields["discipline"].choices)  # pyright: ignore[reportAttributeAccessIssue]
    if discipline not in choices:
        discipline = next(iter(choices), "")
    shown = result_choices(discipline)
    current = form.initial.get("result") if not form.is_bound else None
    if current and current not in dict(shown):
        # Never silently replace a stored value that no longer fits.
        shown.append((current, str(dict(Result.choices).get(current, current))))
    form.fields["result"].widget.choices = shown  # pyright: ignore[reportAttributeAccessIssue]
    form.fields["discipline"].widget.attrs.update(
        {
            "hx-get": reverse("result_options"),
            "hx-trigger": "change",
            "hx-target": "#id_result",
            "hx-swap": "innerHTML",
            "hx-include": "#id_discipline, #id_result",
        }
    )


def routes_at(gym_name: str, query: str = ""):
    """IndoorRoutes at the named Gym (ignoring case), name matched ignoring case."""
    return IndoorRoute.objects.filter(
        gym__name__iexact=gym_name.strip(), name__icontains=query.strip()
    ).select_related("gym")


def route_by_id(raw: object) -> IndoorRoute | None:
    """The IndoorRoute with this id, or None for a missing or malformed id."""
    text = str(raw or "")
    if not (text.isascii() and text.isdigit()):
        return None
    return IndoorRoute.objects.select_related("gym").filter(pk=int(text)).first()


class AscentForm(forms.Form):
    """Quick-add: logs an IndoorAscent of a chosen IndoorRoute, or of a new one.

    A new Route needs a Gym name (created if unknown), a name, a type and a grade.
    Names are not unique within a Gym, so a new Route is never matched to an
    existing one by name: the athlete picks a search match instead.
    """

    route = forms.IntegerField(required=False, widget=forms.HiddenInput)
    gym = forms.CharField(max_length=200, required=False, label="Gym")
    name = forms.CharField(max_length=200, required=False, label="Route name")
    route_type = forms.ChoiceField(
        choices=INDOOR_ROUTE_TYPE_CHOICES,
        required=False,
        label="Type",
    )
    grade = forms.ChoiceField(required=False)
    grade_system = forms.ChoiceField(
        choices=[("", "Default for type"), *GradeSystem.choices], required=False
    )
    discipline = forms.ChoiceField(choices=Discipline.choices)
    result = forms.ChoiceField(choices=Result.choices)
    rests = forms.IntegerField(min_value=1, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(
        self, *args, session: Session, route: IndoorRoute | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.session = session
        search = {
            "autocomplete": "off",
            "hx-get": reverse("route_search", args=[session.pk]),
            "hx-trigger": "input changed delay:250ms",
            "hx-target": "#route-matches",
            "hx-include": "#id_gym, #id_name",
        }
        self.fields["name"].widget.attrs.update(search)
        self.fields["gym"].widget.attrs.update(search)
        self.fields["grade"].choices = grade_choices(  # pyright: ignore[reportAttributeAccessIssue]
            self.data.get("route_type", "") if self.is_bound else "",
            self.data.get("grade_system", "") if self.is_bound else "",
        )
        for trigger in ("route_type", "grade_system"):
            self.fields[trigger].widget.attrs.update(
                {
                    "hx-get": reverse("grade_options"),
                    "hx-trigger": "change",
                    "hx-target": "#id_grade",
                    "hx-swap": "innerHTML",
                    "hx-include": "#id_route_type, #id_grade_system",
                }
            )
        self.chosen: IndoorRoute | None = route or self._route_from_data()
        if self.chosen:
            # The chosen Route already has its grade; ignore any stale posted value.
            self.fields["grade"] = forms.CharField(required=False)
            self.fields["route"].initial = self.chosen.pk
            allowed = DISCIPLINES_BY_ROUTE_TYPE[RouteType(self.chosen.route_type)]
            self.fields["discipline"].choices = [(d.value, d.label) for d in allowed]  # pyright: ignore[reportAttributeAccessIssue]
        if not self.is_bound:
            last = (
                IndoorAscent.objects.filter(session=session).last()
                or IndoorAscent.objects.order_by("created_at", "id").last()
            )
            if last:
                if not self.chosen or last.discipline in dict(
                    self.fields["discipline"].choices  # pyright: ignore[reportAttributeAccessIssue]
                ):
                    self.fields["discipline"].initial = last.discipline
                if not self.chosen:
                    self.fields["gym"].initial = last.route.gym.name
                    self.fields["route_type"].initial = last.route.route_type
                    self.fields["grade"].choices = grade_choices(last.route.route_type)  # pyright: ignore[reportAttributeAccessIssue]

        shown = (
            self.data.get("discipline", "")
            if self.is_bound
            else self.fields["discipline"].initial or ""
        )
        narrow_results(self, shown)

    def _route_from_data(self) -> IndoorRoute | None:
        return route_by_id(self.data.get("route") if self.is_bound else None)

    def clean(self):
        cleaned = super().clean() or {}
        if self.errors:
            return cleaned
        route = self.chosen
        self._gym: Gym | None = None
        if route is None:
            gym_name = cleaned["gym"].strip()
            name = cleaned["name"].strip()
            if not gym_name:
                self.add_error("gym", "Gym is required.")
            if not name:
                self.add_error("name", "Route name is required.")
            if not cleaned["route_type"]:
                self.add_error("route_type", "Choose top-rope, sport or boulder.")
            if self.errors:
                return cleaned
            self._gym = Gym.objects.filter(name__iexact=gym_name).first()
            route = IndoorRoute(
                name=name,
                grade=cleaned["grade"],
                grade_system=cleaned["grade_system"],
                route_type=cleaned["route_type"],
                gym=self._gym or Gym(name=gym_name),
            )
            try:
                route.clean()
            except ValidationError as error:
                for field, messages in error.message_dict.items():
                    self.add_error(field if field in self.fields else None, messages)
                return cleaned
        self._route = route
        self._ascent = IndoorAscent(
            session=self.session,
            route=route,
            discipline=cleaned["discipline"],
            result=cleaned["result"],
            rests=cleaned["rests"],
            notes=cleaned["notes"],
        )
        try:
            self._ascent.clean()
        except ValidationError as error:
            for field, messages in error.message_dict.items():
                self.add_error(field if field in self.fields else None, messages)
        return cleaned

    def save(self) -> IndoorAscent:
        with transaction.atomic():
            if self._route.pk is None:
                self._gym = self._gym or Gym.objects.named(self._route.gym.name)
                self._route.gym = self._gym
                self._route.save()
            self._ascent.route = self._route
            self._ascent.save()
        return self._ascent


class AscentEditForm(forms.ModelForm):
    """Edit an existing Ascent; validates exactly like adding (Ascent.clean)."""

    class Meta:
        model = IndoorAscent
        fields = ["discipline", "result", "rests", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = DISCIPLINES_BY_ROUTE_TYPE[RouteType(self.instance.route.route_type)]
        self.fields["discipline"].choices = [(d.value, d.label) for d in allowed]  # pyright: ignore[reportAttributeAccessIssue]
        self.fields["rests"].widget.attrs["min"] = 1
        narrow_results(
            self,
            self.data.get("discipline", "")
            if self.is_bound
            else self.instance.discipline,
        )


class GymForm(forms.ModelForm):
    class Meta:
        model = Gym
        fields = ["name", "city", "country", "website"]

    def clean_name(self) -> str:
        name = self.cleaned_data["name"].strip()
        clash = Gym.objects.filter(name__iexact=name).exclude(pk=self.instance.pk)
        if clash.exists():
            raise ValidationError(f"A Gym called {clash.first()} already exists.")
        return name
