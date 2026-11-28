from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("logbook", "0006_ascent_date_and_session_end_date"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="indoorascent",
            options={"ordering": ["date", "created_at", "id"]},
        ),
        migrations.AlterField(
            model_name="indoorascent",
            name="date",
            field=models.DateField(blank=True),
        ),
        migrations.AlterField(
            model_name="session",
            name="date",
            field=models.DateField(verbose_name="start date"),
        ),
        migrations.RemoveField(
            model_name="session",
            name="activity_type",
        ),
        migrations.RemoveField(
            model_name="session",
            name="indoor_outdoor",
        ),
        migrations.RemoveField(
            model_name="session",
            name="location",
        ),
    ]
