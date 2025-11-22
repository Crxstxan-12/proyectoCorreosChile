from django.contrib import admin
from .models import TipoPaquete, Remitente, Destinatario, Paquete, HistorialPaquete, RutaPaquete, PuntoEntrega


@admin.register(TipoPaquete)
class TipoPaqueteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'peso_max_kg', 'tarifa_base', 'tiempo_estimado_dias', 'activo']
    list_filter = ['activo', 'tiempo_estimado_dias']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']


@admin.register(Remitente)
class RemitenteAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'email', 'telefono', 'numero_documento', 'comuna']
    search_fields = ['nombre_completo', 'email', 'numero_documento', 'telefono']
    list_filter = ['comuna', 'region']
    ordering = ['nombre_completo']


@admin.register(Destinatario)
class DestinatarioAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'email', 'telefono', 'comuna', 'horario_preferido']
    search_fields = ['nombre_completo', 'email', 'telefono']
    list_filter = ['comuna', 'region']
    ordering = ['nombre_completo']


@admin.register(PuntoEntrega)
class PuntoEntregaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'direccion', 'comuna', 'activo']
    search_fields = ['nombre', 'direccion', 'comuna']
    list_filter = ['tipo', 'comuna', 'region', 'activo']
    ordering = ['nombre']
    readonly_fields = ['latitud', 'longitud']


class HistorialPaqueteInline(admin.TabularInline):
    model = HistorialPaquete
    extra = 0
    readonly_fields = ['fecha_cambio', 'estado_anterior', 'estado_nuevo', 'ubicacion', 'observacion']
    ordering = ['-fecha_cambio']


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ['codigo_seguimiento', 'remitente', 'destinatario', 'tipo_paquete', 
                    'estado', 'peso_kg', 'monto_total', 'fecha_creacion']
    search_fields = ['codigo_seguimiento', 'remitente__nombre_completo', 'remitente__numero_documento',
                     'destinatario__nombre_completo', 'destinatario__email']
    list_filter = ['estado', 'tipo_paquete', 'fecha_creacion', 'forma_pago']
    readonly_fields = ['codigo_seguimiento', 'fecha_creacion', 'ultima_actualizacion']
    ordering = ['-fecha_creacion']
    inlines = [HistorialPaqueteInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo_seguimiento', 'tipo_paquete', 'estado', 'fecha_creacion')
        }),
        ('Dimensiones y Peso', {
            'fields': ('peso_kg', 'largo_cm', 'ancho_cm', 'alto_cm')
        }),
        ('Remitente', {
            'fields': ('remitente',)
        }),
        ('Destinatario', {
            'fields': ('destinatario',)
        }),
        ('Precio y Pago', {
            'fields': ('monto_total', 'forma_pago', 'pagado')
        }),
        ('Opciones de Entrega', {
            'fields': ('instrucciones_especiales',)
        }),
        ('Información Adicional', {
            'fields': ('descripcion_contenido', 'valor_declarado', 'ultima_actualizacion')
        })
    )


@admin.register(HistorialPaquete)
class HistorialPaqueteAdmin(admin.ModelAdmin):
    list_display = ['paquete', 'estado_anterior', 'estado_nuevo', 'fecha_cambio', 'ubicacion']
    search_fields = ['paquete__codigo_seguimiento', 'ubicacion']
    list_filter = ['estado_nuevo', 'fecha_cambio']
    readonly_fields = ['fecha_cambio']
    ordering = ['-fecha_cambio']


@admin.register(RutaPaquete)
class RutaPaqueteAdmin(admin.ModelAdmin):
    list_display = ['paquete', 'orden_en_ruta', 'origen', 'destino', 'fecha_salida', 'completado']
    search_fields = ['paquete__codigo_seguimiento', 'origen', 'destino']
    list_filter = ['completado', 'fecha_salida']
    ordering = ['paquete', 'orden_en_ruta']