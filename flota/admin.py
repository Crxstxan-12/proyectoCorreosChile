from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum

from .models import TipoVehiculo, Vehiculo, MantenimientoVehiculo, RepuestoVehiculo, UsoRepuestoMantenimiento


@admin.register(TipoVehiculo)
class TipoVehiculoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'capacidad_carga_kg', 'capacidad_volumen_m3', 'es_activo', 'vehiculos_count']
    list_filter = ['es_activo', 'capacidad_carga_kg']
    search_fields = ['nombre', 'descripcion']
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(vehiculos_count=Count('vehiculos'))
    
    def vehiculos_count(self, obj):
        return obj.vehiculos_count
    vehiculos_count.short_description = 'Vehículos'


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_placa', 'marca', 'modelo', 'año_fabricacion', 'tipo_vehiculo', 'conductor_asignado_link',
        'estado_colored', 'kilometraje_actual', 'fecha_ultimo_mantenimiento'
    ]
    list_filter = ['estado', 'tipo_vehiculo', 'marca', 'año_fabricacion']
    search_fields = ['numero_placa', 'marca', 'modelo', 'numero_chasis', 'numero_motor']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información General', {
            'fields': ('numero_placa', 'marca', 'modelo', 'año_fabricacion', 'tipo_vehiculo', 'estado')
        }),
        ('Especificaciones Técnicas', {
            'fields': (
                'capacidad_carga_kg', 'capacidad_volumen_m3', 'numero_chasis',
                'numero_motor', 'consumo_promedio_km'
            )
        }),
        ('Asignación y Mantenimiento', {
            'fields': (
                'conductor_asignado', 'kilometraje_actual', 'fecha_ultimo_mantenimiento',
                'proximo_mantenimiento_km', 'fecha_adquisicion'
            )
        }),
        ('Información del Sistema', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tipo_vehiculo', 'conductor_asignado__usuario')
    
    def conductor_asignado_link(self, obj):
        if obj.conductor_asignado:
            url = reverse('admin:conductores_conductor_change', args=[obj.conductor_asignado.id])
            return format_html('<a href="{}">{}</a>', url, obj.conductor_asignado.usuario.get_full_name())
        return "Sin asignar"
    conductor_asignado_link.short_description = 'Conductor Asignado'
    
    def estado_colored(self, obj):
        colors = {
            'disponible': 'green',
            'en_uso': 'blue',
            'mantenimiento': 'orange',
            'fuera_servicio': 'red',
            'reparacion': 'purple',
            'vendido': 'gray'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_colored.short_description = 'Estado'
    
    actions = ['marcar_en_mantenimiento', 'marcar_disponible']
    
    def marcar_en_mantenimiento(self, request, queryset):
        queryset.update(estado='mantenimiento')
        self.message_user(request, f'{queryset.count()} vehículos marcados como en mantenimiento')
    marcar_en_mantenimiento.short_description = 'Marcar como en mantenimiento'
    
    def marcar_disponible(self, request, queryset):
        queryset.update(estado='disponible')
        self.message_user(request, f'{queryset.count()} vehículos marcados como disponibles')
    marcar_disponible.short_description = 'Marcar como disponible'


@admin.register(MantenimientoVehiculo)
class MantenimientoVehiculoAdmin(admin.ModelAdmin):
    list_display = [
        'vehiculo', 'tipo_mantenimiento', 'estado_colored', 'fecha_programada',
        'fecha_fin', 'kilometraje_actual', 'costo_total_display', 'proveedor_servicio'
    ]
    list_filter = ['estado', 'tipo_mantenimiento', 'fecha_programada', 'fecha_fin']
    search_fields = ['vehiculo__numero_placa', 'vehiculo__marca', 'vehiculo__modelo', 'descripcion', 'proveedor_servicio']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'costo_total']
    
    fieldsets = (
        ('Información del Mantenimiento', {
            'fields': ('vehiculo', 'tipo_mantenimiento', 'titulo', 'descripcion', 'estado')
        }),
        ('Fechas y Kilometraje', {
            'fields': ('fecha_programada', 'fecha_inicio', 'fecha_fin', 'kilometraje_actual')
        }),
        ('Costos y Proveedor', {
            'fields': ('costo_mano_obra', 'costo_repuestos', 'costo_total', 'proveedor_servicio')
        }),
        ('Trabajo Realizado', {
            'fields': ('trabajo_realizado', 'duracion_horas'),
            'classes': ('collapse',)
        }),
        ('Información del Sistema', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehiculo__tipo_vehiculo')
    
    def estado_colored(self, obj):
        colors = {
            'programado': 'blue',
            'en_proceso': 'orange',
            'completado': 'green',
            'cancelado': 'red',
            'aplazado': 'purple'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_colored.short_description = 'Estado'
    
    def costo_total_display(self, obj):
        return f"${obj.costo_total:,.0f}"
    costo_total_display.short_description = 'Costo Total'
    
    actions = ['marcar_completado', 'marcar_programado']
    
    def marcar_completado(self, request, queryset):
        from datetime import datetime
        queryset.update(estado='completado', fecha_fin=datetime.now())
        self.message_user(request, f'{queryset.count()} mantenimientos marcados como completados')
    marcar_completado.short_description = 'Marcar como completado'
    
    def marcar_programado(self, request, queryset):
        queryset.update(estado='programado', fecha_fin=None)
        self.message_user(request, f'{queryset.count()} mantenimientos marcados como programados')
    marcar_programado.short_description = 'Marcar como programado'


@admin.register(RepuestoVehiculo)
class RepuestoVehiculoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'cantidad_stock_colored',
        'cantidad_minima', 'precio_unitario', 'proveedor_principal', 'stock_status'
    ]
    list_filter = ['proveedor_principal']
    search_fields = ['codigo', 'nombre', 'descripcion', 'proveedor_principal']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información del Repuesto', {
            'fields': ('codigo', 'nombre', 'descripcion')
        }),
        ('Stock y Precio', {
            'fields': ('cantidad_stock', 'cantidad_minima', 'precio_unitario')
        }),
        ('Proveedor', {
            'fields': ('proveedor_principal',)
        }),
        ('Información del Sistema', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request)
    
    def cantidad_stock_colored(self, obj):
        if obj.cantidad_stock <= obj.cantidad_minima:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', obj.cantidad_stock)
        elif obj.cantidad_stock <= obj.cantidad_minima * 1.5:
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>', obj.cantidad_stock)
        else:
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', obj.cantidad_stock)
    cantidad_stock_colored.short_description = 'Stock'
    
    def stock_status(self, obj):
        if obj.cantidad_stock <= obj.cantidad_minima:
            return format_html('<span style="color: red;">⚠️ Bajo Stock</span>')
        elif obj.cantidad_stock <= obj.cantidad_minima * 1.5:
            return format_html('<span style="color: orange;">⚡ Stock Medio</span>')
        else:
            return format_html('<span style="color: green;">✅ Stock Alto</span>')
    stock_status.short_description = 'Estado Stock'
    
    actions = ['marcar_bajo_stock', 'actualizar_stock']
    
    def marcar_bajo_stock(self, request, queryset):
        for repuesto in queryset:
            repuesto.cantidad_minima = repuesto.cantidad_stock + 10
            repuesto.save()
        self.message_user(request, f'Stock mínimo actualizado para {queryset.count()} repuestos')
    marcar_bajo_stock.short_description = 'Ajustar stock mínimo'


@admin.register(UsoRepuestoMantenimiento)
class UsoRepuestoMantenimientoAdmin(admin.ModelAdmin):
    list_display = ['repuesto', 'mantenimiento_link', 'cantidad_utilizada', 'costo_unitario', 'costo_total', 'fecha_creacion']
    search_fields = ['repuesto__codigo', 'repuesto__nombre', 'mantenimiento__vehiculo__numero_placa']
    readonly_fields = ['fecha_creacion', 'costo_total']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('repuesto', 'mantenimiento__vehiculo__tipo_vehiculo')
    
    def mantenimiento_link(self, obj):
        url = reverse('admin:flota_mantenimientovehiculo_change', args=[obj.mantenimiento.id])
        return format_html('<a href="{}">{} - {}</a>', 
                          url, 
                          obj.mantenimiento.vehiculo.numero_placa,
                          obj.mantenimiento.get_tipo_mantenimiento_display())
    mantenimiento_link.short_description = 'Mantenimiento'
    
    def costo_total(self, obj):
        return obj.cantidad_utilizada * obj.costo_unitario
    costo_total.short_description = 'Costo Total'
