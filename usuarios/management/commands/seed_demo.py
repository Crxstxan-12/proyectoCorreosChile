from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from envios.models import Envio
from seguimiento.models import EventoSeguimiento
from notificaciones.models import Notificacion
from reclamos.models import Reclamo
from usuarios.models import Perfil

class Command(BaseCommand):
    help = "Populate demo data"

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
        if created:
            user.set_password("demo12345")
            user.save()
        Perfil.objects.get_or_create(user=user, defaults={"rol": "usuario"})

        envios = []
        base = [
            ("ENV-0001", "en_transito", "Santiago", "Valparaíso"),
            ("ENV-0002", "en_planta", "Concepción", "La Serena"),
            ("ENV-0003", "en_reparto", "Antofagasta", "Copiapó"),
            ("ENV-0004", "pendiente", "Rancagua", "Temuco"),
            ("ENV-0005", "entregado", "Iquique", "Arica"),
        ]
        for codigo, estado, origen, destino in base:
            e, _ = Envio.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "estado": estado,
                    "origen": origen,
                    "destino": destino,
                    "destinatario_nombre": "Cliente Demo",
                    "direccion_destino": "Av. Ejemplo 123",
                    "usuario": user,
                    "peso_kg": 1.50,
                    "costo": 3500,
                },
            )
            envios.append(e)

        for e in envios:
            EventoSeguimiento.objects.get_or_create(
                envio=e,
                estado=e.estado,
                ubicacion="Centro de Distribución",
                defaults={"observacion": "Evento generado", "registrado_en": timezone.now()},
            )

        for e in envios[:3]:
            Notificacion.objects.get_or_create(
                titulo=f"Actualización {e.codigo}",
                mensaje="Su envío ha cambiado de estado",
                tipo="info",
                canal="web",
                usuario=user,
                envio=e,
            )

        for i, e in enumerate(envios[:2], start=1):
            Reclamo.objects.get_or_create(
                numero=f"REC-{i:04d}",
                defaults={
                    "tipo": "retraso",
                    "estado": "abierto",
                    "descripcion": "Demora en la entrega",
                    "usuario": user,
                    "envio": e,
                },
            )

        self.stdout.write(self.style.SUCCESS("Datos de prueba creados/actualizados"))