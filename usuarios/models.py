from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


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

    def __str__(self):
        return f"{self.user.username} - {self.rol}"