from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import datetime, timedelta

from conductores.models import Conductor
from flota.models import Vehiculo


class TipoPaquete(models.Model):
    """Tipos de paquetes que maneja CorreosChile"""
    
    TIPOS_ENVIO = [
        ('carta', 'Carta'),
        ('sobre', 'Sobre'),
        ('paquete_pequeno', 'Paquete Pequeño'),
        ('paquete_mediano', 'Paquete Mediano'),
        ('paquete_grande', 'Paquete Grande'),
        ('paquete_extra_grande', 'Paquete Extra Grande'),
        ('documento_urgente', 'Documento Urgente'),
        ('valija', 'Valija'),
        ('caja_registrada', 'Caja Registrada'),
    ]
    
    nombre = models.CharField(max_length=50, choices=TIPOS_ENVIO, unique=True)
    descripcion = models.TextField(blank=True)
    dimensiones_max = models.CharField(max_length=100, blank=True, help_text="Dimensiones máximas permitidas")
    peso_max_kg = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    tarifa_base = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tarifa_por_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tiempo_estimado_dias = models.IntegerField(default=3, help_text="Tiempo estimado de entrega en días")
    requiere_firma = models.BooleanField(default=False)
    seguro_incluido = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tipo de Paquete"
        verbose_name_plural = "Tipos de Paquetes"
        ordering = ['nombre']
    
    def __str__(self):
        return self.get_nombre_display()


class Remitente(models.Model):
    """Información del remitente"""
    
    TIPO_DOCUMENTO = [
        ('rut', 'RUT'),
        ('pasaporte', 'Pasaporte'),
        ('dni', 'DNI'),
        ('otro', 'Otro'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO, default='rut')
    numero_documento = models.CharField(max_length=20, validators=[
        RegexValidator(regex=r'^[0-9kK\-]+$', message='Ingrese un documento válido')
    ])
    nombre_completo = models.CharField(max_length=200)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, validators=[
        RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Ingrese un teléfono válido')
    ])
    direccion = models.TextField()
    comuna = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10, blank=True)
    
    # Campos de auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    es_cliente_frecuente = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Remitente"
        verbose_name_plural = "Remitentes"
        ordering = ['nombre_completo']
        unique_together = ['tipo_documento', 'numero_documento']
    
    def __str__(self):
        return f"{self.nombre_completo} ({self.numero_documento})"


class Destinatario(models.Model):
    """Información del destinatario"""
    
    TIPO_DOCUMENTO = [
        ('rut', 'RUT'),
        ('pasaporte', 'Pasaporte'),
        ('dni', 'DNI'),
        ('otro', 'Otro'),
    ]
    
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO, default='rut')
    numero_documento = models.CharField(max_length=20, validators=[
        RegexValidator(regex=r'^[0-9kK\-]+$', message='Ingrese un documento válido')
    ])
    nombre_completo = models.CharField(max_length=200)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, validators=[
        RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Ingrese un teléfono válido')
    ])
    direccion = models.TextField()
    comuna = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10, blank=True)
    
    # Información adicional para entrega
    instrucciones_entrega = models.TextField(blank=True, help_text="Instrucciones especiales para la entrega")
    horario_preferido = models.CharField(max_length=100, blank=True, help_text="Ej: Mañanas, tardes, 9:00-18:00")
    es_direccion_comercial = models.BooleanField(default=False)
    
    # Campos de auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Destinatario"
        verbose_name_plural = "Destinatarios"
        ordering = ['nombre_completo']
        unique_together = ['tipo_documento', 'numero_documento']
    
    def __str__(self):
        return f"{self.nombre_completo} ({self.numero_documento})"


class Paquete(models.Model):
    """Información principal del paquete/envío"""
    
    ESTADO_PAQUETE = [
        ('registrado', 'Registrado'),
        ('en_almacen', 'En Almacén'),
        ('en_transito', 'En Tránsito'),
        ('en_reparto', 'En Reparto'),
        ('entregado', 'Entregado'),
        ('entrega_fallida', 'Entrega Fallida'),
        ('devuelto', 'Devuelto al Remitente'),
        ('perdido', 'Perdido'),
        ('danado', 'Dañado'),
    ]
    
    PRIORIDAD_ENVIO = [
        ('normal', 'Normal'),
        ('urgente', 'Urgente'),
        ('express', 'Express'),
        ('programado', 'Programado'),
    ]
    
    # Código único de seguimiento
    codigo_seguimiento = models.CharField(max_length=20, unique=True, db_index=True)
    codigo_barras = models.CharField(max_length=50, blank=True)
    codigo_qr = models.CharField(max_length=200, blank=True)
    
    # Información del envío
    tipo_paquete = models.ForeignKey(TipoPaquete, on_delete=models.PROTECT)
    remitente = models.ForeignKey(Remitente, on_delete=models.PROTECT, related_name='paquetes_enviados')
    destinatario = models.ForeignKey(Destinatario, on_delete=models.PROTECT, related_name='paquetes_recibidos')
    
    # Dimensiones y peso
    peso_kg = models.DecimalField(max_digits=8, decimal_places=2)
    largo_cm = models.IntegerField(default=0)
    ancho_cm = models.IntegerField(default=0)
    alto_cm = models.IntegerField(default=0)
    volumen_cm3 = models.IntegerField(default=0)
    
    # Estado y prioridad
    estado = models.CharField(max_length=20, choices=ESTADO_PAQUETE, default='registrado')
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_ENVIO, default='normal')
    
    # Información de valor y seguro
    valor_declarado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monto_seguro = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    requiere_seguro = models.BooleanField(default=False)
    
    # Información de pago
    forma_pago = models.CharField(max_length=50, choices=[
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('contra_entrega', 'Contra Entrega'),
        ('cuenta_corriente', 'Cuenta Corriente'),
    ], default='efectivo')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pagado = models.BooleanField(default=False)
    
    # Información de entrega
    fecha_estimada_entrega = models.DateField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)
    intentos_entrega = models.IntegerField(default=0)
    
    # Información de recepción
    quien_recibe = models.CharField(max_length=200, blank=True)
    relacion_destinatario = models.CharField(max_length=100, blank=True)
    firma_entrega = models.TextField(blank=True)  # Base64 de la firma digital
    foto_entrega = models.ImageField(upload_to='entregas/', blank=True, null=True)
    
    # Observaciones y contenido
    descripcion_contenido = models.TextField()
    observaciones = models.TextField(blank=True)
    instrucciones_especiales = models.TextField(blank=True)
    
    # Información de rastreo
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    ubicacion_actual = models.CharField(max_length=200, blank=True)
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario_creacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='paquetes_creados')
    
    class Meta:
        verbose_name = "Paquete"
        verbose_name_plural = "Paquetes"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['codigo_seguimiento']),
            models.Index(fields=['estado']),
            models.Index(fields=['remitente']),
            models.Index(fields=['destinatario']),
            models.Index(fields=['fecha_creacion']),
        ]
    
    def __str__(self):
        return f"Paquete {self.codigo_seguimiento} - {self.get_estado_display()}"
    
    def save(self, *args, **kwargs):
        # Calcular volumen automáticamente
        if self.largo_cm and self.ancho_cm and self.alto_cm:
            self.volumen_cm3 = self.largo_cm * self.ancho_cm * self.alto_cm
        
        # Generar código de seguimiento si no existe
        if not self.codigo_seguimiento:
            self.codigo_seguimiento = self.generar_codigo_seguimiento()
        
        super().save(*args, **kwargs)
    
    def generar_codigo_seguimiento(self):
        """Generar código único de seguimiento"""
        import random
        import string
        
        # Formato: CC + AÑO + MES + DÍA + 6 dígitos aleatorios
        fecha = timezone.now()
        fecha_str = fecha.strftime('%y%m%d')
        random_digits = ''.join(random.choices(string.digits, k=6))
        
        return f"CC{fecha_str}{random_digits}"
    
    def actualizar_estado(self, nuevo_estado, observacion="", usuario=None):
        """Actualizar el estado del paquete y registrar en el historial"""
        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.save()
        
        # Registrar en el historial
        HistorialPaquete.objects.create(
            paquete=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            observacion=observacion,
            usuario=usuario
        )
        
        return True
    
    def calcular_tarifa(self):
        """Calcular la tarifa base del envío"""
        tarifa = self.tipo_paquete.tarifa_base
        
        # Agregar cargo por peso adicional
        if self.peso_kg > self.tipo_paquete.peso_max_kg:
            peso_extra = self.peso_kg - self.tipo_paquete.peso_max_kg
            tarifa += peso_extra * self.tipo_paquete.tarifa_por_kg
        
        # Agregar cargo por prioridad
        if self.prioridad == 'urgente':
            tarifa *= 1.5
        elif self.prioridad == 'express':
            tarifa *= 2.0
        
        return round(tarifa, 2)
    
    def dias_en_transito(self):
        """Calcular días en tránsito"""
        if self.fecha_entrega_real:
            return (self.fecha_entrega_real.date() - self.fecha_creacion.date()).days
        else:
            return (timezone.now().date() - self.fecha_creacion.date()).days
    
    def esta_atrasado(self):
        """Verificar si el paquete está atrasado"""
        if self.estado in ['entregado', 'devuelto', 'perdido', 'danado']:
            return False
        
        if self.fecha_estimada_entrega:
            return timezone.now().date() > self.fecha_estimada_entrega
        
        # Si no hay fecha estimada, usar el tiempo estándar del tipo de paquete
        fecha_limite = self.fecha_creacion.date() + timedelta(days=self.tipo_paquete.tiempo_estimado_dias)
        return timezone.now().date() > fecha_limite


class HistorialPaquete(models.Model):
    """Historial de cambios de estado del paquete"""
    
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE, related_name='historial')
    estado_anterior = models.CharField(max_length=20, choices=Paquete.ESTADO_PAQUETE)
    estado_nuevo = models.CharField(max_length=20, choices=Paquete.ESTADO_PAQUETE)
    observacion = models.TextField(blank=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    ubicacion = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Historial de Paquete"
        verbose_name_plural = "Historial de Paquetes"
        ordering = ['-fecha_cambio']
    
    def __str__(self):
        return f"{self.paquete.codigo_seguimiento}: {self.estado_anterior} → {self.estado_nuevo}"


class RutaPaquete(models.Model):
    """Ruta que sigue el paquete"""
    
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE, related_name='rutas')
    origen = models.CharField(max_length=200)
    destino = models.CharField(max_length=200)
    fecha_salida = models.DateTimeField(null=True, blank=True)
    fecha_llegada = models.DateTimeField(null=True, blank=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
    conductor = models.ForeignKey(Conductor, on_delete=models.SET_NULL, null=True, blank=True)
    orden_en_ruta = models.IntegerField(default=1)
    completado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Ruta de Paquete"
        verbose_name_plural = "Rutas de Paquetes"
        ordering = ['orden_en_ruta']
    
    def __str__(self):
        return f"{self.paquete.codigo_seguimiento}: {self.origen} → {self.destino}"


class PuntoEntrega(models.Model):
    """Puntos de entrega (sucursales, casillas, etc.)"""
    
    TIPO_PUNTO = [
        ('sucursal', 'Sucursal'),
        ('casilla', 'Casilla Postal'),
        ('centro_reparto', 'Centro de Reparto'),
        ('punto_retiro', 'Punto de Retiro'),
        ('locker', 'Locker Inteligente'),
        ('agencia', 'Agencia'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_PUNTO, default='sucursal')
    direccion = models.TextField()
    comuna = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10, blank=True)
    
    # Coordenadas GPS
    latitud = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Información de contacto
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Horarios
    horario_apertura = models.TimeField(default="09:00:00")
    horario_cierre = models.TimeField(default="18:00:00")
    dias_atencion = models.CharField(max_length=50, default="Lunes a Viernes")
    
    # Capacidad
    capacidad_maxima = models.IntegerField(default=1000)
    capacidad_actual = models.IntegerField(default=0)
    
    # Estado
    activo = models.BooleanField(default=True)
    es_centro_distribucion = models.BooleanField(default=False)
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Punto de Entrega"
        verbose_name_plural = "Puntos de Entrega"
        ordering = ['region', 'comuna', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.comuna}"
    
    def capacidad_disponible(self):
        return self.capacidad_maxima - self.capacidad_actual
    
    def esta_lleno(self):
        return self.capacidad_actual >= self.capacidad_maxima
    
    def esta_abierto(self):
        """Verificar si el punto está abierto en este momento"""
        if not self.activo:
            return False
        
        ahora = timezone.now().time()
        # Verificar día de la semana
        dia_actual = timezone.now().strftime('%A')
        if 'Lunes a Viernes' in self.dias_atencion and dia_actual in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            return self.horario_apertura <= ahora <= self.horario_cierre
        elif 'Sábado' in self.dias_atencion and dia_actual == 'Saturday':
            return self.horario_apertura <= ahora <= self.horario_cierre
        elif 'Domingo' in self.dias_atencion and dia_actual == 'Sunday':
            return self.horario_apertura <= ahora <= self.horario_cierre
        
        return False
