from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Perfil(models.Model):
    # Opciones de roles disponibles
    ROLES = (
        ('administrador', 'Administrador'),
        ('editor', 'Editor'),
        ('usuario', 'Usuario'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )  # Relación uno a uno con el usuario

    rol = models.CharField(
        max_length=20,
        choices=ROLES,
        default='usuario'
    )  # Rol del usuario

    foto = models.ImageField(
        upload_to='fotos_perfil/',
        null=True,
        blank=True
    )  # Foto opcional del perfil
    intentos_fallidos = models.PositiveIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.rol}"

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.get_or_create(user=instance, defaults={'rol': 'usuario'})


class SecurityEvent(models.Model):
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ruta = models.CharField(max_length=255)
    metodo = models.CharField(max_length=10)
    ip = models.GenericIPAddressField(null=True, blank=True)
    status = models.PositiveIntegerField()
    detalle = models.TextField(blank=True, null=True)
    ocurrido_en = models.DateTimeField(default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.status} {self.metodo} {self.ruta}"
