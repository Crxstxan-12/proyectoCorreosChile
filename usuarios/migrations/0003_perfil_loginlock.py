from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_securityevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='intentos_fallidos',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='perfil',
            name='bloqueado_hasta',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]

