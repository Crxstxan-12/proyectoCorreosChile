from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Cliente(models.Model):
    """Modelo extendido para clientes con información adicional"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    # Preferencias de notificación
    preferencias_email = models.BooleanField(default=True)
    preferencias_sms = models.BooleanField(default=True)
    preferencias_whatsapp = models.BooleanField(default=False)
    preferencias_push = models.BooleanField(default=False)
    
    # Configuración de privacidad
    mostrar_telefono = models.BooleanField(default=False)
    mostrar_direccion = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Cliente"
    
    @property
    def nombre_completo(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def total_envios(self):
        return self.envios_cliente.count()
    
    @property
    def envios_activos(self):
        return self.envios_cliente.filter(estado__in=['en_transito', 'en_reparto']).count()


@receiver(post_save, sender=User)
def crear_cliente_usuario(sender, instance, created, **kwargs):
    """Crear automáticamente un perfil de cliente cuando se crea un usuario"""
    if created:
        Cliente.objects.get_or_create(user=instance)


class DireccionEntrega(models.Model):
    """Modelo para guardar direcciones de entrega frecuentes"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='direcciones')
    nombre = models.CharField(max_length=100, help_text="Ej: Casa, Oficina, Casa de mis padres")
    direccion = models.TextField()
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)
    telefono_contacto = models.CharField(max_length=20, blank=True, null=True)
    instrucciones = models.TextField(blank=True, null=True, help_text="Instrucciones especiales de entrega")
    es_principal = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'direcciones_entrega'
        verbose_name = 'Dirección de Entrega'
        verbose_name_plural = 'Direcciones de Entrega'
        ordering = ['-es_principal', '-fecha_creacion']
        
    def __str__(self):
        return f"{self.nombre} - {self.direccion[:50]}..."
    
    def save(self, *args, **kwargs):
        """Asegurar que solo haya una dirección principal por cliente"""
        if self.es_principal:
            # Quitar principal de otras direcciones del mismo cliente
            DireccionEntrega.objects.filter(
                cliente=self.cliente, 
                es_principal=True
            ).update(es_principal=False)
        super().save(*args, **kwargs)


class ActividadCliente(models.Model):
    """Modelo para registrar actividad del cliente"""
    TIPOS_ACTIVIDAD = [
        ('login', 'Inicio de Sesión'),
        ('view_envio', 'Visto de Envío'),
        ('update_perfil', 'Actualización de Perfil'),
        ('cambio_direccion', 'Cambio de Dirección'),
        ('cambio_preferencias', 'Cambio de Preferencias'),
        ('descarga_reporte', 'Descarga de Reporte'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='actividades')
    tipo = models.CharField(max_length=30, choices=TIPOS_ACTIVIDAD)
    descripcion = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'actividades_cliente'
        verbose_name = 'Actividad de Cliente'
        verbose_name_plural = 'Actividades de Clientes'
        ordering = ['-fecha']
        
    def __str__(self):
        return f"{self.cliente.nombre_completo} - {self.get_tipo_display()} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"