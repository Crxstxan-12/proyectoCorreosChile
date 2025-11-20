from django.db import models

class Transportista(models.Model):
    TIPOS = (
        ("empresa", "empresa"),
        ("independiente", "independiente"),
    )

    nombre = models.CharField(max_length=120)
    rut = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="empresa")
    email = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"
