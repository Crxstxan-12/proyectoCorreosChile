from django.db import models
from django.contrib.auth.models import User
from envios.models import Envio
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from notificaciones.models import Notificacion, PreferenciaNotificacion

class Reclamo(models.Model):
    ESTADOS = (
        ("abierto", "abierto"),
        ("en_revision", "en_revision"),
        ("resuelto", "resuelto"),
        ("cerrado", "cerrado"),
    )

    TIPOS = (
        ("perdida", "perdida"),
        ("danio", "danio"),
        ("retraso", "retraso"),
        ("otro", "otro"),
    )

    numero = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="otro")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="abierto")
    descripcion = models.TextField()
    respuesta = models.TextField(null=True, blank=True)
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    envio = models.ForeignKey(Envio, null=True, blank=True, on_delete=models.SET_NULL)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.numero} - {self.estado}"


@receiver(pre_save, sender=Reclamo)
def reclamo_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            prev = sender.objects.get(pk=instance.pk)
            instance._prev_estado = prev.estado
        except sender.DoesNotExist:
            instance._prev_estado = None
    else:
        instance._prev_estado = None


@receiver(post_save, sender=Reclamo)
def reclamo_post_save(sender, instance, created, **kwargs):
    try:
        if created:
            return
        prev = getattr(instance, '_prev_estado', None)
        if prev and prev != instance.estado and instance.usuario:
            pref, _ = PreferenciaNotificacion.objects.get_or_create(usuario=instance.usuario)
            canales = pref.canales_activos() or ["web"]
            for c in canales:
                Notificacion.objects.create(
                    titulo=f"Reclamo actualizado: {instance.numero}",
                    mensaje=(f"Tu reclamo cambió de '{prev}' a '{instance.estado}'. "
                             f"{('Respuesta: ' + instance.respuesta) if instance.respuesta else ''}"),
                    tipo="info",
                    canal=c,
                    usuario=instance.usuario,
                    envio=instance.envio,
                )
    except Exception:
        pass
