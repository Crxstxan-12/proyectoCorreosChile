from django.db import models
from django.contrib.auth.models import User
from envios.models import Envio

class Notificacion(models.Model):
    TIPOS = (
        ("info", "info"),
        ("alerta", "alerta"),
        ("error", "error"),
    )

    CANALES = (
        ("email", "email"),
        ("sms", "sms"),
        ("push", "push"),
        ("web", "web"),
    )

    titulo = models.CharField(max_length=120)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS, default="info")
    canal = models.CharField(max_length=20, choices=CANALES, default="web")
    leida = models.BooleanField(default=False)
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    envio = models.ForeignKey(Envio, null=True, blank=True, on_delete=models.SET_NULL)
    creado_en = models.DateTimeField(auto_now_add=True)
    enviado_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.titulo} - {self.tipo}"

class PreferenciaNotificacion(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferencias_notif')
    canal_web = models.BooleanField(default=True)
    canal_email = models.BooleanField(default=False)
    canal_sms = models.BooleanField(default=False)
    canal_push = models.BooleanField(default=False)

    actualizado_en = models.DateTimeField(auto_now=True)

    def canales_activos(self):
        activos = []
        if self.canal_web:
            activos.append('web')
        if self.canal_email:
            activos.append('email')
        if self.canal_sms:
            activos.append('sms')
        if self.canal_push:
            activos.append('push')
        return activos

    def __str__(self):
        return f"Preferencias de {self.usuario.username}"
