from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import (
    DISCIPLINES_BY_ROUTE_TYPE,
    Ascent,
    Discipline,
    GradeSystem,
    Result,
    Route,
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


def routes_at(session: Session, query: str = ""):
    """Routes at the Session's location, name matched ignoring case."""
    return Route.objects.filter(
        location=session.location, name__icontains=query.strip()
    )


class AscentForm(forms.Form):
    """Quick-add: logs an Ascent of an existing Route, or of a new one.

    A name that already exists at the Session's location (ignoring case) reuses
    that Route rather than creating a duplicate.
    """

    route = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name = forms.CharField(max_length=200, required=False, label="Route name")
    route_type = forms.ChoiceField(
        choices=RouteType.choices, required=False, label="Type"
    )
    grade = forms.CharField(max_length=20, required=False)
    grade_system = forms.ChoiceField(
        choices=[("", "Default for type"), *GradeSystem.choices], required=False
    )
    discipline = forms.ChoiceField(choices=Discipline.choices)
    result = forms.ChoiceField(choices=Result.choices)
    rests = forms.IntegerField(min_value=1, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, session: Session, route: Route | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.fields["name"].widget.attrs.update(
            {
                "autocomplete": "off",
                "hx-get": reverse("route_search", args=[session.pk]),
                "hx-trigger": "input changed delay:250ms",
                "hx-target": "#route-matches",
            }
        )
        self.chosen: Route | None = route or self._route_from_data()
        if self.chosen:
            self.fields["route"].initial = self.chosen.pk
            allowed = DISCIPLINES_BY_ROUTE_TYPE[RouteType(self.chosen.route_type)]
            self.fields["discipline"].choices = [(d.value, d.label) for d in allowed]  # pyright: ignore[reportAttributeAccessIssue]
        if not self.is_bound:
            last = (
                Ascent.objects.filter(session=session).last()
                or Ascent.objects.order_by("created_at", "id").last()
            )
            if last:
                if not self.chosen or last.discipline in dict(
                    self.fields["discipline"].choices  # pyright: ignore[reportAttributeAccessIssue]
                ):
                    self.fields["discipline"].initial = last.discipline
                if not self.chosen:
                    self.fields["route_type"].initial = last.route.route_type

    def _route_from_data(self) -> Route | None:
        raw = self.data.get("route") if self.is_bound else None
        if not raw or not (str(raw).isascii() and str(raw).isdigit()):
            return None
        return routes_at(self.session).filter(pk=int(raw)).first()

    def clean(self):
        cleaned = super().clean() or {}
        if self.errors:
            return cleaned
        route = self.chosen
        if route is None:
            name = cleaned["name"].strip()
            if not name:
                self.add_error("name", "Route name is required.")
                return cleaned
            if not cleaned["route_type"]:
                self.add_error("route_type", "Choose boulder or roped.")
                return cleaned
            existing = (
                routes_at(self.session).filter(name__iexact=name).order_by("pk").first()
            )
            if existing and existing.route_type != cleaned["route_type"]:
                self.add_error(
                    "route_type",
                    f"{existing.name} already exists here as a "
                    f"{existing.get_route_type_display().lower()} Route.",  # pyright: ignore[reportAttributeAccessIssue]
                )
                return cleaned
            route = existing or Route(
                name=name,
                grade=cleaned["grade"].strip(),
                grade_system=cleaned["grade_system"],
                route_type=cleaned["route_type"],
                location=self.session.location,
            )
        self._route = route
        self._ascent = Ascent(
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

    def save(self) -> Ascent:
        with transaction.atomic():
            if self._route.pk is None:
                self._route.save()
            self._ascent.route = self._route
            self._ascent.save()
        return self._ascent


class AscentEditForm(forms.ModelForm):
    """Edit an existing Ascent; validates exactly like adding (Ascent.clean)."""

    class Meta:
        model = Ascent
        fields = ["discipline", "result", "rests", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = DISCIPLINES_BY_ROUTE_TYPE[RouteType(self.instance.route.route_type)]
        self.fields["discipline"].choices = [(d.value, d.label) for d in allowed]  # pyright: ignore[reportAttributeAccessIssue]
        self.fields["rests"].widget.attrs["min"] = 1
