from django.db import models
from envios.models import Envio
from notificaciones.models import Notificacion, PreferenciaNotificacion
from django.db.models.signals import post_save
from django.dispatch import receiver

class EventoSeguimiento(models.Model):
    ESTADOS = (
        ("pendiente", "pendiente"),
        ("en_transito", "en_transito"),
        ("en_planta", "en_planta"),
        ("en_reparto", "en_reparto"),
        ("entregado", "entregado"),
        ("incidencia", "incidencia"),
    )

    envio = models.ForeignKey(Envio, on_delete=models.CASCADE, related_name="eventos")
    estado = models.CharField(max_length=20, choices=ESTADOS)
    ubicacion = models.CharField(max_length=120)
    observacion = models.TextField(null=True, blank=True)
    registrado_en = models.DateTimeField(auto_now_add=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.envio.codigo} - {self.estado} - {self.ubicacion}"

@receiver(post_save, sender=EventoSeguimiento)
def crear_notificacion_envio(sender, instance, created, **kwargs):
    if not created:
        return
    tipo = "info"
    if instance.estado == "incidencia":
        tipo = "alerta"
    usuario = getattr(instance.envio, 'usuario', None)
    if usuario:
        pref, _ = PreferenciaNotificacion.objects.get_or_create(usuario=usuario)
        canales = pref.canales_activos() or ["web"]
        for c in canales:
            Notificacion.objects.create(
                titulo=f"Estado actualizado: {instance.envio.codigo}",
                mensaje=f"El envío cambió a '{instance.estado}' en {instance.ubicacion}",
                tipo=tipo,
                canal=c,
                usuario=usuario,
                envio=instance.envio,
            )
    else:
        Notificacion.objects.create(
            titulo=f"Estado actualizado: {instance.envio.codigo}",
            mensaje=f"El envío cambió a '{instance.estado}' en {instance.ubicacion}",
            tipo=tipo,
            canal="web",
            envio=instance.envio,
        )
