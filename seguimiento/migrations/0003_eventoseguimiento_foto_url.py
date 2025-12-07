from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seguimiento', '0002_eventoseguimiento_lat_eventoseguimiento_lng'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventoseguimiento',
            name='foto_url',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]

