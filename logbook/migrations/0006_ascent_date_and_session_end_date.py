from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def date_ascents_from_their_session(apps, schema_editor):
    IndoorAscent = apps.get_model("logbook", "IndoorAscent")
    Session = apps.get_model("logbook", "Session")
    session_date = Session.objects.filter(pk=OuterRef("session_id")).values("date")
    IndoorAscent.objects.update(date=Subquery(session_date[:1]))


class Migration(migrations.Migration):
    dependencies = [
        ("logbook", "0005_indoor_route_attributes"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        # Nullable only until the rows are filled; 0007 makes it required.
        migrations.AddField(
            model_name="indoorascent",
            name="date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(
            date_ascents_from_their_session, migrations.RunPython.noop
        ),
    ]
