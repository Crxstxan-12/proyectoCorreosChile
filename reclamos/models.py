from django.db import models
from django.contrib.auth.models import User
from envios.models import Envio

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
