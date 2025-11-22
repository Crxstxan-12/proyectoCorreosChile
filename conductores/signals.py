from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Conductor, HistorialEstadoConductor, MetricasConductor
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Conductor)
def crear_metricas_diarias_conductor(sender, instance, created, **kwargs):
    """Crea métricas diarias para el conductor si no existen"""
    if not created:
        # Solo crear si no existe para hoy
        hoy = timezone.now().date()
        metricas_existentes = MetricasConductor.objects.filter(
            conductor=instance,
            fecha=hoy
        ).exists()
        
        if not metricas_existentes:
            MetricasConductor.objects.create(
                conductor=instance,
                fecha=hoy
            )
            logger.info(f"Métricas creadas para conductor {instance.nombre_completo} en fecha {hoy}")


@receiver(post_save, sender=Conductor)
def registrar_cambio_estado_conductor(sender, instance, created, **kwargs):
    """Registra cambios de estado del conductor y envía notificaciones"""
    if not created and hasattr(instance, '_estado_anterior'):
        estado_anterior = instance._estado_anterior
        estado_nuevo = instance.estado
        
        if estado_anterior != estado_nuevo:
            # Crear registro en el historial
            HistorialEstadoConductor.objects.create(
                conductor=instance,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo
            )
            
            # Enviar notificación según el estado
            if estado_nuevo == 'disponible':
                enviar_notificacion_conductor_disponible(instance)
            elif estado_nuevo == 'en_ruta':
                enviar_notificacion_conductor_en_ruta(instance)
            elif estado_nuevo == 'fuera_servicio':
                enviar_notificacion_conductor_fuera_servicio(instance)
            
            logger.info(f"Estado de conductor {instance.nombre_completo} cambió de {estado_anterior} a {estado_nuevo}")


def enviar_notificacion_conductor_disponible(conductor):
    """Envía notificación cuando el conductor se pone disponible"""
    try:
        # Por ahora solo logueamos, después integraremos con el sistema de notificaciones
        logger.info(f"Conductor {conductor.nombre_completo} ahora está disponible")
        
    except Exception as e:
        logger.error(f"Error al enviar notificación de conductor disponible: {e}")


def enviar_notificacion_conductor_en_ruta(conductor):
    """Envía notificación cuando el conductor inicia una ruta"""
    try:
        # Por ahora solo logueamos, después integraremos con el sistema de notificaciones
        logger.info(f"Conductor {conductor.nombre_completo} ha iniciado una ruta")
        
    except Exception as e:
        logger.error(f"Error al enviar notificación de conductor en ruta: {e}")


def enviar_notificacion_conductor_fuera_servicio(conductor):
    """Envía notificación cuando el conductor se pone fuera de servicio"""
    try:
        # Por ahora solo logueamos, después integraremos con el sistema de notificaciones
        logger.info(f"Conductor {conductor.nombre_completo} está fuera de servicio")
        
    except Exception as e:
        logger.error(f"Error al enviar notificación de conductor fuera de servicio: {e}")


@receiver(post_save, sender=User)
def crear_perfil_conductor(sender, instance, created, **kwargs):
    """Crea automáticamente un perfil de conductor cuando se crea un usuario conductor"""
    if created and hasattr(instance, 'groups'):
        from django.contrib.auth.models import Group
        
        # Verificar si el usuario pertenece al grupo de conductores
        try:
            grupo_conductores = Group.objects.get(name='Conductores')
            if grupo_conductores in instance.groups.all():
                # Crear perfil de conductor con datos básicos
                Conductor.objects.get_or_create(
                    usuario=instance,
                    defaults={
                        'licencia_conducir': f'LIC-{instance.username}',
                        'fecha_vencimiento_licencia': timezone.now().date(),
                        'activo': True
                    }
                )
                logger.info(f"Perfil de conductor creado para usuario {instance.username}")
        except Group.DoesNotExist:
            logger.warning("Grupo 'Conductores' no encontrado")
        except Exception as e:
            logger.error(f"Error al crear perfil de conductor: {e}")


# Guardar el estado anterior antes de guardar
@receiver(post_save, sender=Conductor)
def guardar_estado_anterior(sender, instance, **kwargs):
    """Guarda el estado anterior para comparación"""
    try:
        conductor_original = Conductor.objects.get(pk=instance.pk)
        instance._estado_anterior = conductor_original.estado
    except Conductor.DoesNotExist:
        instance._estado_anterior = None