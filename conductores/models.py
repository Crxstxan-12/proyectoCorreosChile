from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from envios.models import Envio


class Conductor(models.Model):
    """Perfil extendido para conductores con funciones móviles"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    licencia_conducir = models.CharField(max_length=50, unique=True)
    fecha_vencimiento_licencia = models.DateField()
    vehiculo_asignado = models.CharField(max_length=100, blank=True, null=True)
    placa_vehiculo = models.CharField(max_length=20, blank=True, null=True)
    
    # Estado del conductor
    ESTADOS_CONDUCTOR = [
        ('disponible', 'Disponible'),
        ('en_ruta', 'En Ruta'),
        ('descanso', 'En Descanso'),
        ('fuera_servicio', 'Fuera de Servicio'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_CONDUCTOR, default='disponible')
    
    # Ubicación actual
    latitud_actual = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_actual = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    ultima_actualizacion_ubicacion = models.DateTimeField(blank=True, null=True)
    
    # Configuración de la app móvil
    dispositivo_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    token_notificacion = models.CharField(max_length=255, blank=True, null=True)
    app_version = models.CharField(max_length=20, blank=True, null=True)
    
    # Métricas
    total_envios_entregados = models.IntegerField(default=0)
    total_kilometros_recorridos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_ingreso = models.DateField(default=timezone.now)
    
    # Horario de trabajo
    hora_inicio_jornada = models.TimeField(blank=True, null=True)
    hora_fin_jornada = models.TimeField(blank=True, null=True)
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conductor'
        verbose_name_plural = 'Conductores'
        ordering = ['usuario__first_name', 'usuario__last_name']

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.licencia_conducir}"

    @property
    def nombre_completo(self):
        return self.usuario.get_full_name() or self.usuario.username

    @property
    def esta_disponible(self):
        return self.estado == 'disponible' and self.activo

    @property
    def licencia_vencida(self):
        if self.fecha_vencimiento_licencia:
            return timezone.now().date() > self.fecha_vencimiento_licencia
        return False

    def actualizar_ubicacion(self, latitud, longitud):
        """Actualiza la ubicación actual del conductor"""
        self.latitud_actual = latitud
        self.longitud_actual = longitud
        self.ultima_actualizacion_ubicacion = timezone.now()
        self.save(update_fields=['latitud_actual', 'longitud_actual', 'ultima_actualizacion_ubicacion'])

    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado del conductor"""
        if nuevo_estado in [choice[0] for choice in self.ESTADOS_CONDUCTOR]:
            self.estado = nuevo_estado
            self.save(update_fields=['estado'])
            # Registrar el cambio de estado
            HistorialEstadoConductor.objects.create(
                conductor=self,
                estado_anterior=self.estado,
                estado_nuevo=nuevo_estado
            )


class RutaConductor(models.Model):
    """Ruta asignada a un conductor para un día de trabajo"""
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name='rutas')
    fecha = models.DateField(default=timezone.now)
    nombre_ruta = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    
    # Estado de la ruta
    ESTADOS_RUTA = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_RUTA, default='pendiente')
    
    # Métricas de la ruta
    total_envios = models.IntegerField(default=0)
    envios_entregados = models.IntegerField(default=0)
    envios_fallidos = models.IntegerField(default=0)
    distancia_total_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tiempo_estimado_minutos = models.IntegerField(default=0)
    
    # Tiempos
    hora_inicio = models.DateTimeField(blank=True, null=True)
    hora_fin = models.DateTimeField(blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ruta del Conductor'
        verbose_name_plural = 'Rutas de Conductores'
        ordering = ['-fecha', 'nombre_ruta']
        unique_together = ['conductor', 'fecha', 'nombre_ruta']

    def __str__(self):
        return f"{self.nombre_ruta} - {self.conductor.nombre_completo} ({self.fecha})"

    @property
    def progreso(self):
        if self.total_envios > 0:
            return (self.envios_entregados / self.total_envios) * 100
        return 0

    def actualizar_progreso(self):
        """Actualiza el progreso basado en los envíos de la ruta"""
        envios_ruta = self.envios_ruta.all()
        self.total_envios = envios_ruta.count()
        self.envios_entregados = envios_ruta.filter(envio__estado='entregado').count()
        self.envios_fallidos = envios_ruta.filter(envio__estado='fallido').count()
        self.save(update_fields=['total_envios', 'envios_entregados', 'envios_fallidos'])


class EnvioRuta(models.Model):
    """Relación entre envíos y rutas de conductores"""
    ruta = models.ForeignKey(RutaConductor, on_delete=models.CASCADE, related_name='envios_ruta')
    envio = models.ForeignKey(Envio, on_delete=models.CASCADE, related_name='rutas')
    orden_entrega = models.IntegerField(default=1)
    
    # Estado específico del envío en la ruta
    ESTADOS_ENVIO_RUTA = [
        ('pendiente', 'Pendiente'),
        ('en_camino', 'En Camino'),
        ('entregado', 'Entregado'),
        ('fallido', 'Fallido'),
        ('reprogramado', 'Reprogramado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_ENVIO_RUTA, default='pendiente')
    
    # Información de entrega
    fecha_intento_entrega = models.DateTimeField(blank=True, null=True)
    motivo_fallo = models.TextField(blank=True, null=True)
    firma_digital = models.TextField(blank=True, null=True)  # Base64 de la firma
    foto_entrega = models.ImageField(upload_to='fotos_entrega/', blank=True, null=True)
    
    # Ubicación de entrega
    latitud_entrega = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_entrega = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    
    # Notas del conductor
    notas = models.TextField(blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Envío en Ruta'
        verbose_name_plural = 'Envíos en Rutas'
        ordering = ['orden_entrega']
        unique_together = ['ruta', 'envio']

    def __str__(self):
        return f"{self.envio.codigo} - Ruta: {self.ruta.nombre_ruta}"

    def marcar_entregado(self, firma_digital=None, foto=None, latitud=None, longitud=None):
        """Marca el envío como entregado"""
        self.estado = 'entregado'
        self.fecha_intento_entrega = timezone.now()
        self.firma_digital = firma_digital
        if foto:
            self.foto_entrega = foto
        if latitud and longitud:
            self.latitud_entrega = latitud
            self.longitud_entrega = longitud
        self.save()
        
        # Actualizar el estado del envío principal
        self.envio.estado = 'entregado'
        self.envio.save(update_fields=['estado'])
        
        # Actualizar progreso de la ruta
        self.ruta.actualizar_progreso()

    def marcar_fallido(self, motivo, latitud=None, longitud=None):
        """Marca el envío como fallido"""
        self.estado = 'fallido'
        self.fecha_intento_entrega = timezone.now()
        self.motivo_fallo = motivo
        if latitud and longitud:
            self.latitud_entrega = latitud
            self.longitud_entrega = longitud
        self.save()
        
        # Actualizar el estado del envío principal
        self.envio.estado = 'fallido'
        self.envio.save(update_fields=['estado'])
        
        # Actualizar progreso de la ruta
        self.ruta.actualizar_progreso()


class HistorialEstadoConductor(models.Model):
    """Historial de cambios de estado del conductor"""
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name='historial_estados')
    estado_anterior = models.CharField(max_length=20, choices=Conductor.ESTADOS_CONDUCTOR)
    estado_nuevo = models.CharField(max_length=20, choices=Conductor.ESTADOS_CONDUCTOR)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Historial de Estado del Conductor'
        verbose_name_plural = 'Historial de Estados de Conductores'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"{self.conductor.nombre_completo}: {self.estado_anterior} → {self.estado_nuevo}"


class IncidenciaConductor(models.Model):
    """Incidencias reportadas por conductores"""
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name='incidencias')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    
    TIPOS_INCIDENCIA = [
        ('accidente', 'Accidente'),
        ('averia_vehiculo', 'Avería del Vehículo'),
        ('problema_entrega', 'Problema en Entrega'),
        ('problema_cliente', 'Problema con Cliente'),
        ('condiciones_climaticas', 'Condiciones Climáticas'),
        ('otro', 'Otro'),
    ]
    tipo = models.CharField(max_length=30, choices=TIPOS_INCIDENCIA)
    
    # Ubicación de la incidencia
    latitud = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    
    # Estado de resolución
    ESTADOS_INCIDENCIA = [
        ('pendiente', 'Pendiente'),
        ('en_revision', 'En Revisión'),
        ('resuelta', 'Resuelta'),
        ('cerrada', 'Cerrada'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_INCIDENCIA, default='pendiente')
    
    # Fotos de evidencia
    foto1 = models.ImageField(upload_to='incidencias/', blank=True, null=True)
    foto2 = models.ImageField(upload_to='incidencias/', blank=True, null=True)
    foto3 = models.ImageField(upload_to='incidencias/', blank=True, null=True)
    
    # Información adicional
    envio_afectado = models.ForeignKey(Envio, on_delete=models.SET_NULL, blank=True, null=True, related_name='incidencias')
    
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Incidencia del Conductor'
        verbose_name_plural = 'Incidencias de Conductores'
        ordering = ['-fecha_reporte']

    def __str__(self):
        return f"{self.titulo} - {self.conductor.nombre_completo}"


class MetricasConductor(models.Model):
    """Métricas diarias del conductor"""
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name='metricas')
    fecha = models.DateField(default=timezone.now)
    
    # Métricas de rendimiento
    total_envios_entregados = models.IntegerField(default=0)
    total_envios_fallidos = models.IntegerField(default=0)
    total_kilometros_recorridos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tiempo_total_trabajado_minutos = models.IntegerField(default=0)
    
    # Eficiencia
    eficiencia_entregas = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Porcentaje
    tiempo_promedio_entrega_minutos = models.IntegerField(default=0)
    
    # Incidencias
    total_incidencias_reportadas = models.IntegerField(default=0)
    
    # Puntuación general
    puntuacion_general = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Métrica del Conductor'
        verbose_name_plural = 'Métricas de Conductores'
        ordering = ['-fecha']
        unique_together = ['conductor', 'fecha']

    def __str__(self):
        return f"Métricas {self.conductor.nombre_completo} - {self.fecha}"

    def calcular_puntuacion(self):
        """Calcula la puntuación general basada en las métricas"""
        puntuacion = 0
        
        # Eficiencia en entregas (0-40 puntos)
        if self.total_envios_entregados + self.total_envios_fallidos > 0:
            eficiencia = (self.total_envios_entregados / (self.total_envios_entregados + self.total_envios_fallidos)) * 100
            puntuacion += (eficiencia * 40) / 100
        
        # Tiempo promedio de entrega (0-30 puntos)
        if self.tiempo_promedio_entrega_minutos <= 15:
            puntuacion += 30
        elif self.tiempo_promedio_entrega_minutos <= 30:
            puntuacion += 20
        elif self.tiempo_promedio_entrega_minutos <= 45:
            puntuacion += 10
        
        # Kilómetros recorridos (0-20 puntos)
        if self.total_kilometros_recorridos >= 50:
            puntuacion += 20
        elif self.total_kilometros_recorridos >= 25:
            puntuacion += 15
        elif self.total_kilometros_recorridos >= 10:
            puntuacion += 10
        
        # Sin incidencias (0-10 puntos)
        if self.total_incidencias_reportadas == 0:
            puntuacion += 10
        
        self.puntuacion_general = round(puntuacion, 1)
        self.save(update_fields=['puntuacion_general'])
