from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('envios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='envio',
            name='fecha_estimada_entrega',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='envio',
            name='eta_actualizado_en',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='envio',
            name='eta_km_restante',
            field=models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='envio',
            name='destino_lat',
            field=models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='envio',
            name='destino_lng',
            field=models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True),
        ),
    ]

