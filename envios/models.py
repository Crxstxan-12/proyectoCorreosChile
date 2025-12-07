from django.db import models
from django.contrib.auth.models import User
from transportista.models import Transportista
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

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
    fecha_estimada_entrega = models.DateTimeField(null=True, blank=True)
    eta_actualizado_en = models.DateTimeField(null=True, blank=True)
    eta_km_restante = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    destino_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destino_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.codigo} - {self.estado}"

    def total_bultos(self):
        return self.bultos.count()

    def bultos_entregados(self):
        return self.bultos.filter(entregado=True).count()

    def bultos_pendientes(self):
        return self.bultos.filter(entregado=False).count()

    def actualizar_estado_por_bultos(self):
        total = self.total_bultos()
        entregados = self.bultos_entregados()
        if total > 0 and entregados == total and self.estado != 'entregado':
            self.estado = 'entregado'
            self.save(update_fields=['estado', 'actualizado_en'])

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

@receiver(post_save, sender=Bulto)
def actualizar_envio_por_bulto_guardado(sender, instance, **kwargs):
    envio = instance.envio
    total = envio.bultos.count()
    entregados = envio.bultos.filter(entregado=True).count()
    if total > 0 and entregados == total and envio.estado != 'entregado':
        envio.estado = 'entregado'
        envio.save(update_fields=['estado', 'actualizado_en'])

@receiver(post_delete, sender=Bulto)
def actualizar_envio_por_bulto_eliminado(sender, instance, **kwargs):
    envio = instance.envio
    total = envio.bultos.count()
    if total == 0:
        return
    entregados = envio.bultos.filter(entregado=True).count()
    if entregados == total and envio.estado != 'entregado':
        envio.estado = 'entregado'
        envio.save(update_fields=['estado', 'actualizado_en'])
