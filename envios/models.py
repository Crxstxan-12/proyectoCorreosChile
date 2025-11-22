from django.db import models
from django.contrib.auth.models import User
from transportista.models import Transportista

class Envio(models.Model):
    ESTADOS = (
        ("pendiente", "pendiente"),
        ("en_transito", "en_transito"),
        ("entregado", "entregado"),
        ("devuelto", "devuelto"),
        ("cancelado", "cancelado"),
    )

    codigo = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    origen = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    destinatario_nombre = models.CharField(max_length=100)
    direccion_destino = models.CharField(max_length=255)
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    transportista = models.ForeignKey(Transportista, null=True, blank=True, on_delete=models.SET_NULL)
    peso_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.codigo} - {self.estado}"

class Bulto(models.Model):
    envio = models.ForeignKey(Envio, on_delete=models.CASCADE, related_name="bultos")
    codigo_barras = models.CharField(max_length=100)
    peso_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    foto_url = models.URLField(null=True, blank=True)
    entregado = models.BooleanField(default=False)
    entregado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("envio", "codigo_barras")

    def __str__(self):
        return f"{self.envio.codigo} - {self.codigo_barras}"
