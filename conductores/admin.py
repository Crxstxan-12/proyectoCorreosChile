from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import (
    Conductor, RutaConductor, EnvioRuta, HistorialEstadoConductor,
    IncidenciaConductor, MetricasConductor
)


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_completo', 'licencia_conducir', 'estado', 'vehiculo_asignado',
        'total_envios_entregados', 'activo', 'licencia_vencida_display',
        'ultima_actualizacion_ubicacion'
    ]
    list_filter = ['estado', 'activo', 'fecha_ingreso', 'vehiculo_asignado']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'licencia_conducir', 'placa_vehiculo']
    readonly_fields = [
        'total_envios_entregados', 'total_kilometros_recorridos', 'fecha_creacion',
        'fecha_actualizacion', 'ultima_actualizacion_ubicacion', 'licencia_vencida_display'
    ]
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('usuario', 'telefono', 'licencia_conducir', 'fecha_vencimiento_licencia')
        }),
        ('Vehículo', {
            'fields': ('vehiculo_asignado', 'placa_vehiculo')
        }),
        ('Estado y Ubicación', {
            'fields': ('estado', 'latitud_actual', 'longitud_actual', 'ultima_actualizacion_ubicacion')
        }),
        ('App Móvil', {
            'fields': ('dispositivo_id', 'app_version', 'token_notificacion'),
            'classes': ('collapse',)
        }),
        ('Horario', {
            'fields': ('hora_inicio_jornada', 'hora_fin_jornada')
        }),
        ('Métricas', {
            'fields': ('total_envios_entregados', 'total_kilometros_recorridos'),
            'classes': ('collapse',)
        }),
        ('Configuración', {
            'fields': ('activo', 'fecha_ingreso', 'fecha_creacion', 'fecha_actualizacion')
        })
    )
    
    def licencia_vencida_display(self, obj):
        if obj.licencia_vencida:
            return format_html('<span style="color: red;">✗ Vencida</span>')
        return format_html('<span style="color: green;">✓ Vigente</span>')
    licencia_vencida_display.short_description = 'Licencia'
    
    def nombre_completo(self, obj):
        return obj.nombre_completo
    nombre_completo.short_description = 'Nombre'
    
    actions = ['marcar_disponible', 'marcar_fuera_servicio']
    
    def marcar_disponible(self, request, queryset):
        for conductor in queryset:
            conductor.cambiar_estado('disponible')
        self.message_user(request, f"{queryset.count()} conductores marcados como disponibles")
    marcar_disponible.short_description = "Marcar como Disponible"
    
    def marcar_fuera_servicio(self, request, queryset):
        for conductor in queryset:
            conductor.cambiar_estado('fuera_servicio')
        self.message_user(request, f"{queryset.count()} conductores marcados como fuera de servicio")
    marcar_fuera_servicio.short_description = "Marcar como Fuera de Servicio"


class EnvioRutaInline(admin.TabularInline):
    model = EnvioRuta
    extra = 0
    fields = ['envio', 'orden_entrega', 'estado', 'fecha_intento_entrega']
    readonly_fields = ['fecha_intento_entrega']
    ordering = ['orden_entrega']


@admin.register(RutaConductor)
class RutaConductorAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_ruta', 'conductor', 'fecha', 'estado', 'progreso_display',
        'total_envios', 'envios_entregados', 'envios_fallidos', 'hora_inicio',
        'hora_fin'
    ]
    list_filter = ['estado', 'fecha', 'conductor__usuario__first_name']
    search_fields = ['nombre_ruta', 'conductor__usuario__first_name', 'conductor__usuario__last_name']
    readonly_fields = [
        'total_envios', 'envios_entregados', 'envios_fallidos', 'progreso_display',
        'hora_inicio', 'hora_fin', 'fecha_creacion', 'fecha_actualizacion'
    ]
    inlines = [EnvioRutaInline]
    
    fieldsets = (
        ('Información General', {
            'fields': ('conductor', 'nombre_ruta', 'fecha', 'descripcion')
        }),
        ('Estado', {
            'fields': ('estado', 'hora_inicio', 'hora_fin')
        }),
        ('Métricas', {
            'fields': ('total_envios', 'envios_entregados', 'envios_fallidos', 'distancia_total_km', 'tiempo_estimado_minutos')
        }),
        ('Progreso', {
            'fields': ('progreso_display',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    def progreso_display(self, obj):
        progreso = obj.progreso
        color = 'green' if progreso >= 75 else 'orange' if progreso >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white;">'
            '{:.1f}%</div></div>',
            progreso, color, progreso
        )
    progreso_display.short_description = 'Progreso'
    
    actions = ['iniciar_ruta', 'finalizar_ruta']
    
    def iniciar_ruta(self, request, queryset):
        for ruta in queryset:
            if ruta.estado == 'pendiente':
                ruta.estado = 'en_progreso'
                ruta.hora_inicio = timezone.now()
                ruta.save()
                ruta.conductor.cambiar_estado('en_ruta')
        self.message_user(request, f"Rutas iniciadas correctamente")
    iniciar_ruta.short_description = "Iniciar Rutas Seleccionadas"
    
    def finalizar_ruta(self, request, queryset):
        for ruta in queryset:
            if ruta.estado == 'en_progreso':
                ruta.estado = 'completada'
                ruta.hora_fin = timezone.now()
                ruta.save()
                ruta.conductor.cambiar_estado('disponible')
        self.message_user(request, f"Rutas finalizadas correctamente")
    finalizar_ruta.short_description = "Finalizar Rutas Seleccionadas"


@admin.register(EnvioRuta)
class EnvioRutaAdmin(admin.ModelAdmin):
    list_display = [
        'envio', 'ruta', 'orden_entrega', 'estado', 'fecha_intento_entrega',
        'motivo_fallo_corto'
    ]
    list_filter = ['estado', 'fecha_intento_entrega', 'ruta__conductor']
    search_fields = ['envio__codigo', 'ruta__nombre_ruta', 'motivo_fallo']
    readonly_fields = ['fecha_intento_entrega', 'fecha_creacion', 'fecha_actualizacion']
    list_editable = ['orden_entrega']
    ordering = ['ruta', 'orden_entrega']
    
    def motivo_fallo_corto(self, obj):
        if obj.motivo_fallo:
            return obj.motivo_fallo[:50] + '...' if len(obj.motivo_fallo) > 50 else obj.motivo_fallo
        return '-'
    motivo_fallo_corto.short_description = 'Motivo Fallo'
    
    actions = ['marcar_entregado', 'marcar_fallido']
    
    def marcar_entregado(self, request, queryset):
        for envio_ruta in queryset:
            if envio_ruta.estado in ['pendiente', 'en_camino']:
                envio_ruta.marcar_entregado()
        self.message_user(request, f"Envíos marcados como entregados")
    marcar_entregado.short_description = "Marcar como Entregado"
    
    def marcar_fallido(self, request, queryset):
        for envio_ruta in queryset:
            if envio_ruta.estado in ['pendiente', 'en_camino']:
                envio_ruta.marcar_fallido('Marcado como fallido desde administrador')
        self.message_user(request, f"Envíos marcados como fallidos")
    marcar_fallido.short_description = "Marcar como Fallido"


@admin.register(HistorialEstadoConductor)
class HistorialEstadoConductorAdmin(admin.ModelAdmin):
    list_display = ['conductor', 'estado_anterior', 'estado_nuevo', 'fecha_cambio']
    list_filter = ['estado_nuevo', 'fecha_cambio']
    search_fields = ['conductor__usuario__first_name', 'conductor__usuario__last_name']
    readonly_fields = ['conductor', 'estado_anterior', 'estado_nuevo', 'fecha_cambio']
    ordering = ['-fecha_cambio']


@admin.register(IncidenciaConductor)
class IncidenciaConductorAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 'conductor', 'tipo', 'estado', 'fecha_reporte',
        'descripcion_corta'
    ]
    list_filter = ['tipo', 'estado', 'fecha_reporte']
    search_fields = ['titulo', 'descripcion', 'conductor__usuario__first_name']
    readonly_fields = ['fecha_reporte', 'fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información General', {
            'fields': ('conductor', 'titulo', 'tipo', 'descripcion')
        }),
        ('Estado', {
            'fields': ('estado', 'fecha_reporte', 'fecha_resolucion')
        }),
        ('Ubicación', {
            'fields': ('latitud', 'longitud'),
            'classes': ('collapse',)
        }),
        ('Evidencia', {
            'fields': ('foto1', 'foto2', 'foto3'),
            'classes': ('collapse',)
        }),
        ('Envío Afectado', {
            'fields': ('envio_afectado',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    def descripcion_corta(self, obj):
        if obj.descripcion:
            return obj.descripcion[:100] + '...' if len(obj.descripcion) > 100 else obj.descripcion
        return '-'
    descripcion_corta.short_description = 'Descripción'
    
    actions = ['marcar_resuelta']
    
    def marcar_resuelta(self, request, queryset):
        for incidencia in queryset:
            if incidencia.estado in ['pendiente', 'en_revision']:
                incidencia.estado = 'resuelta'
                incidencia.fecha_resolucion = timezone.now()
                incidencia.save()
        self.message_user(request, f"Incidencias marcadas como resueltas")
    marcar_resuelta.short_description = "Marcar como Resuelta"


@admin.register(MetricasConductor)
class MetricasConductorAdmin(admin.ModelAdmin):
    list_display = [
        'conductor', 'fecha', 'total_envios_entregados', 'total_envios_fallidos',
        'eficiencia_entregas', 'tiempo_promedio_entrega_minutos', 'puntuacion_general'
    ]
    list_filter = ['fecha', 'conductor__usuario__first_name']
    search_fields = ['conductor__usuario__first_name', 'conductor__usuario__last_name']
    readonly_fields = ['puntuacion_general', 'fecha_creacion', 'fecha_actualizacion']
    ordering = ['-fecha']
    
    fieldsets = (
        ('Información General', {
            'fields': ('conductor', 'fecha')
        }),
        ('Entregas', {
            'fields': ('total_envios_entregados', 'total_envios_fallidos', 'eficiencia_entregas')
        }),
        ('Rendimiento', {
            'fields': ('total_kilometros_recorridos', 'tiempo_total_trabajado_minutos', 'tiempo_promedio_entrega_minutos')
        }),
        ('Calidad', {
            'fields': ('total_incidencias_reportadas', 'puntuacion_general')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        # No permitir agregar métricas manualmente
        return False
