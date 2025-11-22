from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from envios.models import Envio


class ConfiguracionNotificacion(models.Model):
    """Configuración de preferencias de notificación por cliente"""
    
    CANALES_NOTIFICACION = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push Notification'),
    )
    
    FRECUENCIA_NOTIFICACION = (
        ('inmediata', 'Inmediata'),
        ('diaria', 'Diaria (resumen)'),
        ('semanal', 'Semanal (resumen)'),
    )
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='config_notificacion')
    
    # Preferencias de canal
    canal_email = models.BooleanField(default=True)
    canal_sms = models.BooleanField(default=False)
    canal_whatsapp = models.BooleanField(default=False)
    canal_push = models.BooleanField(default=False)
    
    # Frecuencia general
    frecuencia = models.CharField(max_length=20, choices=FRECUENCIA_NOTIFICACION, default='inmediata')
    
    # Horarios de preferencia (para envíos programados)
    hora_inicio = models.TimeField(default='08:00')
    hora_fin = models.TimeField(default='20:00')
    
    # Zona horaria
    zona_horaria = models.CharField(max_length=50, default='America/Santiago')
    
    # Estado de suscripción
    esta_activa = models.BooleanField(default=True)
    
    # Límite de notificaciones por día (para evitar spam)
    limite_diario = models.IntegerField(default=10)
    
    # Campos de contacto
    telefono_movil = models.CharField(max_length=20, blank=True, null=True)
    token_push = models.CharField(max_length=255, blank=True, null=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuración de {self.usuario.get_full_name() or self.usuario.username}"

    class Meta:
        verbose_name = "Configuración de Notificación"
        verbose_name_plural = "Configuraciones de Notificaciones"


class PlantillaNotificacion(models.Model):
    """Plantillas de notificaciones predefinidas"""
    
    TIPOS_NOTIFICACION = (
        ('envio_creado', 'Envío Creado'),
        ('envio_en_transito', 'Envío en Tránsito'),
        ('envio_en_reparto', 'Envío en Reparto'),
        ('envio_entregado', 'Envío Entregado'),
        ('envio_demorado', 'Envío Demorado'),
        ('envio_en_sucursal', 'Envío en Sucursal'),
        ('reclamo_actualizado', 'Reclamo Actualizado'),
        ('recordatorio_entrega', 'Recordatorio de Entrega'),
        ('confirmacion_horario', 'Confirmación de Horario'),
        ('multibulto_listo', 'Multibulto Listo para Retiro'),
    )
    
    CATEGORIAS_URGENTES = [
        'envio_demorado', 'envio_en_reparto', 'recordatorio_entrega'
    ]
    
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPOS_NOTIFICACION, unique=True)
    
    # Contenido por canal
    asunto_email = models.CharField(max_length=200, blank=True, null=True)
    template_email_html = models.TextField(blank=True, null=True)
    template_email_texto = models.TextField(blank=True, null=True)
    
    template_sms = models.CharField(max_length=160, blank=True, null=True)
    template_whatsapp = models.TextField(max_length=1000, blank=True, null=True)
    template_push = models.CharField(max_length=100, blank=True, null=True)
    
    # Variables dinámicas disponibles
    variables_disponibles = models.TextField(
        help_text="Lista de variables disponibles: {{cliente_nombre}}, {{numero_envio}}, {{direccion}}, etc."
    )
    
    # Prioridad y urgencia
    prioridad = models.IntegerField(default=1, help_text="1-10, donde 10 es máxima prioridad")
    es_urgente = models.BooleanField(default=False)
    
    # Configuración de envío
    requiere_confirmacion = models.BooleanField(default=False)
    tiempo_espera_respuesta = models.IntegerField(default=24, help_text="Horas para esperar respuesta")
    
    # Activación
    esta_activa = models.BooleanField(default=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = "Plantilla de Notificación"
        verbose_name_plural = "Plantillas de Notificaciones"


class NotificacionProgramada(models.Model):
    """Notificaciones programadas para envío futuro"""
    
    ESTADOS_NOTIFICACION = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('error', 'Error'),
        ('cancelada', 'Cancelada'),
        ('expirada', 'Expirada'),
    )
    
    envio = models.ForeignKey(Envio, on_delete=models.CASCADE, related_name='notificaciones')
    plantilla = models.ForeignKey(PlantillaNotificacion, on_delete=models.CASCADE)
    
    # Información del destinatario
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones_recibidas')
    email_destino = models.EmailField(blank=True, null=True)
    telefono_destino = models.CharField(max_length=20, blank=True, null=True)
    
    # Programación
    fecha_programada = models.DateTimeField()
    fecha_envio = models.DateTimeField(blank=True, null=True)
    
    # Canal y contenido
    canal_programado = models.CharField(max_length=20, choices=ConfiguracionNotificacion.CANALES_NOTIFICACION)
    contenido_personalizado = models.JSONField(blank=True, null=True, help_text="Variables personalizadas para el template")
    
    # Estado y tracking
    estado = models.CharField(max_length=20, choices=ESTADOS_NOTIFICACION, default='pendiente')
    intentos_envio = models.IntegerField(default=0)
    
    # Respuesta del cliente
    respuesta_cliente = models.TextField(blank=True, null=True)
    fecha_respuesta = models.DateTimeField(blank=True, null=True)
    
    # Logs y errores
    log_envio = models.TextField(blank=True, null=True)
    error_mensaje = models.TextField(blank=True, null=True)
    
    # Prioridad dinámica
    prioridad = models.IntegerField(default=1)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notificación {self.plantilla.nombre} - {self.destinatario.username}"

    class Meta:
        verbose_name = "Notificación Programada"
        verbose_name_plural = "Notificaciones Programadas"
        ordering = ['fecha_programada', 'prioridad']


class HistorialNotificacion(models.Model):
    """Historial de todas las notificaciones enviadas"""
    
    notificacion_programada = models.ForeignKey(NotificacionProgramada, on_delete=models.CASCADE, related_name='historial')
    
    # Información del envío
    canal_utilizado = models.CharField(max_length=20, choices=ConfiguracionNotificacion.CANALES_NOTIFICACION)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    
    # Contenido final enviado
    asunto = models.CharField(max_length=200, blank=True, null=True)
    contenido = models.TextField()
    
    # Resultado
    fue_exitoso = models.BooleanField(default=True)
    mensaje_error = models.TextField(blank=True, null=True)
    
    # Información técnica
    proveedor_envio = models.CharField(max_length=50, blank=True, null=True)  # ej: SendGrid, Twilio
    id_proveedor = models.CharField(max_length=100, blank=True, null=True)
    
    # Métricas
    tiempo_respuesta_ms = models.IntegerField(blank=True, null=True)
    
    # Feedback del cliente
    fue_leido = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(blank=True, null=True)
    
    # Enlaces de tracking
    link_tracking = models.URLField(blank=True, null=True)
    clicks = models.IntegerField(default=0)

    def __str__(self):
        return f"Historial: {self.notificacion_programada} - {self.fecha_envio}"

    class Meta:
        verbose_name = "Historial de Notificación"
        verbose_name_plural = "Historial de Notificaciones"
        ordering = ['-fecha_envio']


class ListaExclusionNotificacion(models.Model):
    """Gestión de listas de exclusión (clientes que no quieren recibir notificaciones)"""
    
    TIPOS_EXCLUSION = (
        ('temporal', 'Temporal'),
        ('permanente', 'Permanente'),
        ('por_tipo', 'Por Tipo de Notificación'),
    )
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exclusiones_notificacion')
    tipo_exclusion = models.CharField(max_length=20, choices=TIPOS_EXCLUSION, default='temporal')
    
    # Si es por tipo específico
    tipos_notificacion = models.ManyToManyField(PlantillaNotificacion, blank=True)
    
    # Período de exclusión (para temporal)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    
    # Razón de exclusión
    razon = models.TextField(blank=True, null=True)
    
    esta_activa = models.BooleanField(default=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Exclusión: {self.usuario.username} - {self.tipo_exclusion}"

    class Meta:
        verbose_name = "Lista de Exclusión"
        verbose_name_plural = "Listas de Exclusión"


class MetricaNotificacion(models.Model):
    """Métricas de rendimiento del sistema de notificaciones"""
    
    fecha = models.DateField()
    
    # Métricas generales
    total_enviadas = models.IntegerField(default=0)
    total_exitosas = models.IntegerField(default=0)
    total_fallidas = models.IntegerField(default=0)
    
    # Por canal
    email_enviados = models.IntegerField(default=0)
    email_exitosos = models.IntegerField(default=0)
    sms_enviados = models.IntegerField(default=0)
    sms_exitosos = models.IntegerField(default=0)
    whatsapp_enviados = models.IntegerField(default=0)
    whatsapp_exitosos = models.IntegerField(default=0)
    
    # Tiempos de respuesta promedio
    tiempo_promedio_email_ms = models.IntegerField(default=0)
    tiempo_promedio_sms_ms = models.IntegerField(default=0)
    tiempo_promedio_whatsapp_ms = models.IntegerField(default=0)
    
    # Tasa de apertura y clicks
    tasa_apertura_email = models.FloatField(default=0.0)
    tasa_click_email = models.FloatField(default=0.0)
    
    # Reclamos generados
    reclamos_asociados = models.IntegerField(default=0)

    def __str__(self):
        return f"Métricas: {self.fecha}"

    class Meta:
        verbose_name = "Métrica de Notificación"
        verbose_name_plural = "Métricas de Notificaciones"
        unique_together = ['fecha']