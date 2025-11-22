from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Cliente, DireccionEntrega, ActividadCliente


class ClienteInline(admin.StackedInline):
    model = Cliente
    can_delete = False
    verbose_name_plural = 'Información de Cliente'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    inlines = (ClienteInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_cliente_info')
    list_select_related = ('cliente',)
    
    def get_cliente_info(self, obj):
        try:
            cliente = obj.cliente
            return format_html(
                '<span style="color: green;">✓ Cliente</span><br>'
                '<small>Tel: {}<br>Envíos: {}</small>',
                cliente.telefono or 'No registrado',
                cliente.total_envios
            )
        except Cliente.DoesNotExist:
            return format_html('<span style="color: red;">✗ Sin perfil</span>')
    
    get_cliente_info.short_description = 'Info Cliente'


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['user', 'telefono', 'ciudad', 'fecha_registro', 'activo', 'total_envios', 'envios_activos']
    list_filter = ['activo', 'ciudad', 'fecha_registro', 'preferencias_email', 'preferencias_sms']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'telefono']
    readonly_fields = ['fecha_registro', 'total_envios', 'envios_activos']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('user', 'telefono', 'direccion', 'ciudad', 'codigo_postal')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_registro')
        }),
        ('Preferencias de Notificación', {
            'fields': ('preferencias_email', 'preferencias_sms', 'preferencias_whatsapp', 'preferencias_push')
        }),
        ('Privacidad', {
            'fields': ('mostrar_telefono', 'mostrar_direccion')
        }),
        ('Estadísticas', {
            'fields': ('total_envios', 'envios_activos'),
            'classes': ('collapse',)
        }),
    )
    
    def total_envios(self, obj):
        return obj.total_envios()
    
    def envios_activos(self, obj):
        return obj.envios_activos()
    
    total_envios.short_description = 'Total Envíos'
    envios_activos.short_description = 'Envíos Activos'


@admin.register(DireccionEntrega)
class DireccionEntregaAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'nombre', 'ciudad', 'es_principal', 'activa', 'fecha_creacion']
    list_filter = ['activa', 'es_principal', 'ciudad', 'fecha_creacion']
    search_fields = ['cliente__user__username', 'nombre', 'direccion', 'ciudad']
    readonly_fields = ['fecha_creacion']
    
    fieldsets = (
        ('Información de la Dirección', {
            'fields': ('cliente', 'nombre', 'direccion', 'ciudad', 'codigo_postal')
        }),
        ('Contacto', {
            'fields': ('telefono_contacto', 'instrucciones')
        }),
        ('Configuración', {
            'fields': ('es_principal', 'activa', 'fecha_creacion')
        }),
    )


@admin.register(ActividadCliente)
class ActividadClienteAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'tipo', 'descripcion', 'fecha', 'ip_address']
    list_filter = ['tipo', 'fecha']
    search_fields = ['cliente__user__username', 'descripcion', 'ip_address']
    readonly_fields = ['fecha']
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Información de Actividad', {
            'fields': ('cliente', 'tipo', 'descripcion', 'fecha')
        }),
        ('Información Técnica', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # No permitir agregar actividades manualmente
    
    def has_change_permission(self, request, obj=None):
        return False  # No permitir editar actividades


# Re-registrar UserAdmin con el inline
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)
