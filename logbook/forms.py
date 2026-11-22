from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Ascent, Discipline, GradeSystem, Result, Route, RouteType, Session


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


class NewRouteAscentForm(forms.Form):
    """Quick-add: logs an Ascent of a brand-new Route on an indoor Session."""

    name = forms.CharField(max_length=200, label="Route name")
    route_type = forms.ChoiceField(choices=RouteType.choices, label="Type")
    grade = forms.CharField(max_length=20, required=False)
    grade_system = forms.ChoiceField(
        choices=[("", "Default for type"), *GradeSystem.choices], required=False
    )
    discipline = forms.ChoiceField(choices=Discipline.choices)
    result = forms.ChoiceField(choices=Result.choices)
    rests = forms.IntegerField(min_value=1, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, session: Session, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        if not self.is_bound:
            last = (
                Ascent.objects.filter(session=session).last()
                or Ascent.objects.order_by("created_at", "id").last()
            )
            if last:
                self.fields["discipline"].initial = last.discipline
                self.fields["route_type"].initial = last.route.route_type

    def clean(self):
        cleaned = super().clean() or {}
        if self.errors:
            return cleaned
        self._route = Route(
            name=cleaned["name"].strip(),
            grade=cleaned["grade"].strip(),
            grade_system=cleaned["grade_system"],
            route_type=cleaned["route_type"],
            location=self.session.location,
        )
        self._ascent = Ascent(
            session=self.session,
            route=self._route,
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
            self._route.save()
            self._ascent.route = self._route
            self._ascent.save()
        return self._ascent
