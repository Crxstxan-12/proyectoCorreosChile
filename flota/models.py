from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class TipoVehiculo(models.Model):
    """Tipos de vehículos en la flota"""
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    capacidad_carga_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Capacidad máxima en kg")
    capacidad_volumen_m3 = models.DecimalField(max_digits=10, decimal_places=2, help_text="Volumen máximo en m³")
    consumo_combustible_km = models.DecimalField(max_digits=8, decimal_places=2, help_text="Consumo por km")
    es_activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tipo de Vehículo"
        verbose_name_plural = "Tipos de Vehículos"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    """Vehículos de la flota de CorreosChile"""
    
    ESTADO_VEHICULO = [
        ('disponible', 'Disponible'),
        ('en_uso', 'En Uso'),
        ('mantenimiento', 'En Mantenimiento'),
        ('fuera_servicio', 'Fuera de Servicio'),
        ('reparacion', 'En Reparación'),
        ('vendido', 'Vendido/Dado de Baja'),
    ]
    
    COMBUSTIBLE_TIPOS = [
        ('gasolina', 'Gasolina'),
        ('diesel', 'Diesel'),
        ('gas', 'Gas'),
        ('electricidad', 'Electricidad'),
        ('hibrido', 'Híbrido'),
    ]
    
    # Información básica
    numero_placa = models.CharField(max_length=20, unique=True, help_text="Número de patente/placa")
    tipo_vehiculo = models.ForeignKey(TipoVehiculo, on_delete=models.PROTECT, related_name='vehiculos')
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    año_fabricacion = models.PositiveIntegerField(
        validators=[MinValueValidator(1990), MaxValueValidator(2030)]
    )
    
    # Especificaciones técnicas
    numero_chasis = models.CharField(max_length=50, unique=True, help_text="Número de chasis/VIN")
    numero_motor = models.CharField(max_length=50, unique=True, help_text="Número de motor")
    color = models.CharField(max_length=30, blank=True)
    kilometraje_actual = models.PositiveIntegerField(default=0, help_text="Kilometraje actual")
    
    # Combustible y rendimiento
    tipo_combustible = models.CharField(max_length=20, choices=COMBUSTIBLE_TIPOS, default='diesel')
    capacidad_tanque_litros = models.DecimalField(max_digits=8, decimal_places=2, help_text="Capacidad del tanque en litros")
    consumo_promedio_km = models.DecimalField(max_digits=6, decimal_places=2, help_text="Consumo promedio por km")
    
    # Estado y asignación
    estado = models.CharField(max_length=20, choices=ESTADO_VEHICULO, default='disponible')
    ubicacion_actual = models.CharField(max_length=200, blank=True, help_text="Ubicación actual del vehículo")
    latitud_actual = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_actual = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Asignación a conductor
    conductor_asignado = models.OneToOneField(
        'conductores.Conductor', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='vehiculo_conductor'
    )
    
    # Información de seguro y documentación
    compania_seguro = models.CharField(max_length=100, blank=True)
    numero_poliza = models.CharField(max_length=50, blank=True)
    fecha_vencimiento_seguro = models.DateField(null=True, blank=True)
    fecha_vencimiento_revision_tecnica = models.DateField(null=True, blank=True)
    fecha_vencimiento_permiso_circulacion = models.DateField(null=True, blank=True)
    
    # Costos y depreciación
    costo_adquisicion = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Costo de adquisición")
    valor_actual = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Valor actual del vehículo")
    fecha_adquisicion = models.DateField(null=True, blank=True)
    
    # Mantenimiento
    fecha_ultimo_mantenimiento = models.DateField(null=True, blank=True)
    kilometraje_ultimo_mantenimiento = models.PositiveIntegerField(null=True, blank=True)
    proximo_mantenimiento_km = models.PositiveIntegerField(null=True, blank=True)
    proximo_mantenimiento_fecha = models.DateField(null=True, blank=True)
    
    # Observaciones
    observaciones = models.TextField(blank=True, help_text="Observaciones generales del vehículo")
    
    # Control de estado
    es_activo = models.BooleanField(default=True, help_text="Vehículo activo en la flota")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"
        ordering = ['numero_placa']
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.numero_placa}"
    
    @property
    def antiguedad_años(self):
        """Calcula la antigüedad del vehículo en años"""
        from datetime import datetime
        return datetime.now().year - self.año_fabricacion
    
    @property
    def kilometraje_desde_ultimo_mantenimiento(self):
        """Kilometraje recorrido desde el último mantenimiento"""
        if self.kilometraje_ultimo_mantenimiento:
            return self.kilometraje_actual - self.kilometraje_ultimo_mantenimiento
        return self.kilometraje_actual
    
    @property
    def dias_para_proximo_mantenimiento(self):
        """Días hasta el próximo mantenimiento"""
        if self.proximo_mantenimiento_fecha:
            return (self.proximo_mantenimiento_fecha - timezone.now().date()).days
        return None
    
    @property
    def necesita_mantenimiento(self):
        """Indica si el vehículo necesita mantenimiento"""
        if not self.es_activo:
            return False
            
        # Verificar por kilometraje
        if self.proximo_mantenimiento_km and self.kilometraje_actual >= self.proximo_mantenimiento_km:
            return True
            
        # Verificar por fecha
        if self.proximo_mantenimiento_fecha and timezone.now().date() >= self.proximo_mantenimiento_fecha:
            return True
            
        return False
    
    @property
    def documentacion_vencida(self):
        """Lista de documentación vencida"""
        vencidos = []
        hoy = timezone.now().date()
        
        if self.fecha_vencimiento_seguro and hoy >= self.fecha_vencimiento_seguro:
            vencidos.append('Seguro')
            
        if self.fecha_vencimiento_revision_tecnica and hoy >= self.fecha_vencimiento_revision_tecnica:
            vencidos.append('Revisión Técnica')
            
        if self.fecha_vencimiento_permiso_circulacion and hoy >= self.fecha_vencimiento_permiso_circulacion:
            vencidos.append('Permiso de Circulación')
            
        return vencidos
    
    def asignar_conductor(self, conductor):
        """Asigna un conductor al vehículo"""
        if self.conductor_asignado:
            raise ValueError("El vehículo ya tiene un conductor asignado")
        
        self.conductor_asignado = conductor
        self.estado = 'en_uso'
        self.save()
    
    def liberar_conductor(self):
        """Libera el conductor asignado"""
        self.conductor_asignado = None
        if self.estado == 'en_uso':
            self.estado = 'disponible'
        self.save()


class MantenimientoVehiculo(models.Model):
    """Registro de mantenimientos de vehículos"""
    
    TIPO_MANTENIMIENTO = [
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo'),
        ('predictivo', 'Predictivo'),
        ('emergencia', 'Emergencia'),
    ]
    
    ESTADO_MANTENIMIENTO = [
        ('programado', 'Programado'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
        ('aplazado', 'Aplazado'),
    ]
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='mantenimientos')
    tipo_mantenimiento = models.CharField(max_length=20, choices=TIPO_MANTENIMIENTO)
    estado = models.CharField(max_length=20, choices=ESTADO_MANTENIMIENTO, default='programado')
    
    # Información del mantenimiento
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    kilometraje_actual = models.PositiveIntegerField(help_text="Kilometraje del vehículo en el momento del mantenimiento")
    
    # Fechas y duración
    fecha_programada = models.DateField()
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_horas = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Duración en horas")
    
    # Costos
    costo_mano_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo de mano de obra")
    costo_repuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo de repuestos")
    costo_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo total del mantenimiento")
    
    # Proveedor y responsable
    proveedor_servicio = models.CharField(max_length=200, blank=True, help_text="Taller o proveedor del servicio")
    responsable_mantenimiento = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='mantenimientos_responsable'
    )
    
    # Prioridad y urgencia
    prioridad = models.CharField(
        max_length=10,
        choices=[
            ('baja', 'Baja'),
            ('media', 'Media'),
            ('alta', 'Alta'),
            ('urgente', 'Urgente')
        ],
        default='media'
    )
    
    # Documentación
    factura_numero = models.CharField(max_length=50, blank=True)
    garantia_meses = models.PositiveIntegerField(null=True, blank=True, help_text="Meses de garantía del servicio")
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    trabajo_realizado = models.TextField(blank=True, help_text="Descripción detallada del trabajo realizado")
    
    # Control
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Mantenimiento de Vehículo"
        verbose_name_plural = "Mantenimientos de Vehículos"
        ordering = ['-fecha_programada']
    
    def __str__(self):
        return f"{self.titulo} - {self.vehiculo.numero_placa}"
    
    def save(self, *args, **kwargs):
        # Calcular costo total automáticamente
        self.costo_total = self.costo_mano_obra + self.costo_repuestos
        super().save(*args, **kwargs)
    
    @property
    def duracion_dias(self):
        """Calcula la duración en días"""
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days
        return None
    
    @property
    def esta_vencida_garantia(self):
        """Verifica si la garantía está vencida"""
        if self.garantia_meses and self.fecha_fin:
            from dateutil.relativedelta import relativedelta
            fecha_vencimiento = self.fecha_fin + relativedelta(months=self.garantia_meses)
            return timezone.now() > fecha_vencimiento
        return False


class RepuestoVehiculo(models.Model):
    """Catálogo de repuestos para vehículos"""
    
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    marca = models.CharField(max_length=100, blank=True)
    modelo_compatible = models.CharField(max_length=200, blank=True, help_text="Modelos de vehículo compatibles")
    
    # Información de inventario
    cantidad_stock = models.PositiveIntegerField(default=0)
    cantidad_minima = models.PositiveIntegerField(default=5, help_text="Cantidad mínima en stock")
    ubicacion_almacen = models.CharField(max_length=100, blank=True, help_text="Ubicación en el almacén")
    
    # Precios
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio unitario")
    precio_proveedor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Precio del proveedor")
    
    # Proveedor
    proveedor_principal = models.CharField(max_length=200, blank=True)
    tiempo_entrega_dias = models.PositiveIntegerField(default=7, help_text="Días de entrega del proveedor")
    
    # Control
    es_activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Repuesto de Vehículo"
        verbose_name_plural = "Repuestos de Vehículos"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
    
    @property
    def necesita_reabastecimiento(self):
        """Indica si el repuesto necesita reabastecimiento"""
        return self.cantidad_stock <= self.cantidad_minima
    
    @property
    def valor_total_stock(self):
        """Valor total del stock"""
        return self.cantidad_stock * self.precio_unitario


class UsoRepuestoMantenimiento(models.Model):
    """Repuestos utilizados en mantenimientos"""
    
    mantenimiento = models.ForeignKey(MantenimientoVehiculo, on_delete=models.CASCADE, related_name='repuestos_utilizados')
    repuesto = models.ForeignKey(RepuestoVehiculo, on_delete=models.PROTECT, related_name='usos')
    cantidad_utilizada = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo unitario al momento del uso")
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Uso de Repuesto"
        verbose_name_plural = "Usos de Repuestos"
    
    def __str__(self):
        return f"{self.repuesto.nombre} - {self.mantenimiento.titulo}"
    
    @property
    def costo_total(self):
        """Costo total del repuesto utilizado"""
        return self.cantidad_utilizada * self.costo_unitario
    
    def save(self, *args, **kwargs):
        # Actualizar el costo unitario del repuesto actual
        if not self.costo_unitario:
            self.costo_unitario = self.repuesto.precio_unitario
        
        # Descontar del stock
        if self.pk is None:  # Solo al crear
            self.repuesto.cantidad_stock -= self.cantidad_utilizada
            self.repuesto.save()
        
        super().save(*args, **kwargs)
