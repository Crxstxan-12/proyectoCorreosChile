from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone

from .models import Cliente, ActividadCliente
from envios.models import Envio
from notificaciones_mejoradas.models import NotificacionProgramada
from notificaciones_mejoradas.services import NotificationEngine


@receiver(post_save, sender=User)
def crear_perfil_cliente(sender, instance, created, **kwargs):
    """Crear perfil de cliente automáticamente cuando se crea un usuario"""
    if created:
        Cliente.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def registrar_login_cliente(sender, request, user, **kwargs):
    """Registrar actividad de login del cliente"""
    try:
        cliente = user.cliente
        ActividadCliente.objects.create(
            cliente=cliente,
            tipo='login',
            descripcion='Inicio de sesión en el sistema',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    except Cliente.DoesNotExist:
        pass


@receiver(post_save, sender=Envio)
def notificar_nuevo_envio_cliente(sender, instance, created, **kwargs):
    """Notificar al cliente cuando se crea un nuevo envío"""
    if created and instance.usuario:
        try:
            cliente = instance.usuario.cliente
            
            # Crear notificación programada
            engine = NotificationEngine()
            
            # Contexto para el template
            context = {
                'cliente_nombre': cliente.nombre_completo,
                'envio_codigo': instance.codigo,
                'destinatario': instance.destinatario_nombre,
                'destino': instance.destino,
                'fecha_creacion': instance.creado_en.strftime('%d/%m/%Y %H:%M'),
            }
            
            # Programar notificación inmediata
            engine.crear_notificacion(
                cliente=cliente,
                tipo='envio_creado',
                contexto=context,
                programado_para=kwargs.get('programado_para') or timezone.now(),
                prioridad='alta'
            )
            
        except (Cliente.DoesNotExist, AttributeError):
            # Si no hay cliente asociado, no hacer nada
            pass


def get_client_ip(request):
    """Obtener IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip