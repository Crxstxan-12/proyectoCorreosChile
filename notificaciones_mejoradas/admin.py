from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    ConfiguracionNotificacion,
    PlantillaNotificacion,
    NotificacionProgramada,
    HistorialNotificacion,
    ListaExclusionNotificacion,
    MetricaNotificacion
)


@admin.register(ConfiguracionNotificacion)
class ConfiguracionNotificacionAdmin(admin.ModelAdmin):
    list_display = [
        'usuario', 'canal_email', 'canal_sms', 'canal_whatsapp',
        'frecuencia', 'esta_activa', 'limite_diario', 'telefono_movil'
    ]
    list_filter = ['frecuencia', 'esta_activa', 'canal_email', 'canal_sms', 'canal_whatsapp']
    search_fields = ['usuario__username', 'usuario__email', 'telefono_movil']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información General', {
            'fields': ('usuario', 'esta_activa', 'creado_en', 'actualizado_en')
        }),
        ('Canales de Notificación', {
            'fields': ('canal_email', 'canal_sms', 'canal_whatsapp', 'canal_push')
        }),
        ('Configuración de Envío', {
            'fields': ('frecuencia', 'hora_inicio', 'hora_fin', 'zona_horaria', 'limite_diario')
        }),
        ('Información de Contacto', {
            'fields': ('telefono_movil', 'token_push')
        }),
    )


@admin.register(PlantillaNotificacion)
class PlantillaNotificacionAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'tipo', 'prioridad', 'es_urgente', 'esta_activa',
        'requiere_confirmacion', 'tiempo_espera_respuesta'
    ]
    list_filter = ['tipo', 'es_urgente', 'esta_activa', 'requiere_confirmacion', 'prioridad']
    search_fields = ['nombre', 'tipo', 'variables_disponibles']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'tipo', 'esta_activa', 'creado_en', 'actualizado_en')
        }),
        ('Prioridad y Urgencia', {
            'fields': ('prioridad', 'es_urgente')
        }),
        ('Configuración de Envío', {
            'fields': ('requiere_confirmacion', 'tiempo_espera_respuesta')
        }),
        ('Plantilla Email', {
            'fields': ('asunto_email', 'template_email_html', 'template_email_texto'),
            'classes': ('collapse',)
        }),
        ('Plantillas SMS y WhatsApp', {
            'fields': ('template_sms', 'template_whatsapp', 'template_push'),
            'classes': ('collapse',)
        }),
        ('Variables Disponibles', {
            'fields': ('variables_disponibles',),
            'description': 'Variables que puedes usar en las plantillas: {{cliente_nombre}}, {{numero_envio}}, etc.'
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Personalizar ayuda para los campos
        if 'asunto_email' in form.base_fields:
            form.base_fields['asunto_email'].help_text = 'Ej: Tu envío {{numero_envio}} está en camino'
        if 'template_email_html' in form.base_fields:
            form.base_fields['template_email_html'].help_text = 'HTML completo del email. Usa {{variables}} para personalizar.'
        if 'template_sms' in form.base_fields:
            form.base_fields['template_sms'].help_text = 'Máximo 160 caracteres. Ej: Hola {{cliente_nombre}}, tu envío {{numero_envio}} está en camino.'
        return form


@admin.register(NotificacionProgramada)
class NotificacionProgramadaAdmin(admin.ModelAdmin):
    list_display = [
        'destinatario', 'plantilla', 'canal_programado', 'fecha_programada',
        'estado', 'intentos_envio', 'fecha_envio', 'prioridad'
    ]
    list_filter = ['estado', 'canal_programado', 'plantilla__tipo', 'prioridad']
    search_fields = [
        'destinatario__username', 'destinatario__email',
        'plantilla__nombre', 'email_destino', 'telefono_destino'
    ]
    readonly_fields = ['creado_en', 'actualizado_en', 'fecha_envio', 'intentos_envio']
    
    fieldsets = (
        ('Información General', {
            'fields': ('plantilla', 'destinatario', 'envio', 'creado_en', 'actualizado_en')
        }),
        ('Programación', {
            'fields': ('fecha_programada', 'fecha_envio', 'prioridad')
        }),
        ('Destinatario y Canal', {
            'fields': ('canal_programado', 'email_destino', 'telefono_destino')
        }),
        ('Estado y Seguimiento', {
            'fields': ('estado', 'intentos_envio', 'contenido_personalizado')
        }),
        ('Respuesta del Cliente', {
            'fields': ('respuesta_cliente', 'fecha_respuesta'),
            'classes': ('collapse',)
        }),
        ('Logs y Errores', {
            'fields': ('log_envio', 'error_mensaje'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['enviar_notificaciones_pendientes', 'cancelar_notificaciones']
    
    def enviar_notificaciones_pendientes(self, request, queryset):
        """Acción para enviar notificaciones pendientes manualmente"""
        pendientes = queryset.filter(estado='pendiente')
        count = pendientes.count()
        
        if count > 0:
            from .tasks import procesar_notificaciones_pendientes
            procesar_notificaciones_pendientes.delay(list(pendientes.values_list('id', flat=True)))
            self.message_user(request, f'{count} notificaciones programadas para envío.')
        else:
            self.message_user(request, 'No hay notificaciones pendientes seleccionadas.')
    
    enviar_notificaciones_pendientes.short_description = "Enviar notificaciones pendientes seleccionadas"
    
    def cancelar_notificaciones(self, request, queryset):
        """Cancelar notificaciones pendientes"""
        actualizadas = queryset.filter(estado='pendiente').update(estado='cancelada')
        self.message_user(request, f'{actualizadas} notificaciones canceladas.')
    
    cancelar_notificaciones.short_description = "Cancelar notificaciones pendientes"


@admin.register(HistorialNotificacion)
class HistorialNotificacionAdmin(admin.ModelAdmin):
    list_display = [
        'notificacion_programada', 'canal_utilizado', 'fecha_envio',
        'fue_exitoso', 'fue_leido', 'clicks', 'tiempo_respuesta_ms'
    ]
    list_filter = ['canal_utilizado', 'fue_exitoso', 'fue_leido']
    search_fields = [
        'notificacion_programada__destinatario__username',
        'notificacion_programada__plantilla__nombre',
        'proveedor_envio'
    ]
    readonly_fields = ['fecha_envio', 'contenido']
    
    fieldsets = (
        ('Información General', {
            'fields': ('notificacion_programada', 'canal_utilizado', 'fecha_envio', 'proveedor_envio')
        }),
        ('Contenido Enviado', {
            'fields': ('asunto', 'contenido')
        }),
        ('Resultado', {
            'fields': ('fue_exitoso', 'mensaje_error', 'tiempo_respuesta_ms')
        }),
        ('Feedback del Cliente', {
            'fields': ('fue_leido', 'fecha_lectura', 'link_tracking', 'clicks'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # No permitir agregar manualmente historial
        return False
    
    def has_change_permission(self, request, obj=None):
        # Solo lectura
        return False


@admin.register(ListaExclusionNotificacion)
class ListaExclusionNotificacionAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo_exclusion', 'esta_activa', 'fecha_inicio', 'fecha_fin']
    list_filter = ['tipo_exclusion', 'esta_activa']
    search_fields = ['usuario__username', 'usuario__email', 'razon']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información General', {
            'fields': ('usuario', 'tipo_exclusion', 'esta_activa', 'razon')
        }),
        ('Período de Exclusión', {
            'fields': ('fecha_inicio', 'fecha_fin', 'creado_en', 'actualizado_en')
        }),
        ('Tipos de Notificación Excluidos', {
            'fields': ('tipos_notificacion',),
            'description': 'Solo aplica para exclusiones por tipo específico'
        }),
    )


@admin.register(MetricaNotificacion)
class MetricaNotificacionAdmin(admin.ModelAdmin):
    list_display = [
        'fecha', 'total_enviadas', 'total_exitosas', 'total_fallidas',
        'tasa_apertura_email', 'tasa_click_email', 'reclamos_asociados'
    ]
    readonly_fields = [field.name for field in MetricaNotificacion._meta.fields]
    
    def has_add_permission(self, request):
        # Las métricas se generan automáticamente
        return False
    
    def has_change_permission(self, request, obj=None):
        # Solo lectura
        return False
