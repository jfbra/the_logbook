from django import forms
from django.utils import timezone

from .models import Session


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
