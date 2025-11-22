from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('envios', '0003_envio_usuario'),
        ('transportista', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='envio',
            name='transportista',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.SET_NULL, to='transportista.transportista'),
        ),
    ]