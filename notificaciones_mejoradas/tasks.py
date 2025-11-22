from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .models import NotificacionProgramada, HistorialNotificacion, MetricaNotificacion
from .services import NotificationEngine

logger = logging.getLogger(__name__)


@shared_task
def procesar_notificaciones_pendientes(notificacion_ids=None):
    """
    Procesa notificaciones pendientes de envío
    
    Args:
        notificacion_ids: Lista opcional de IDs específicos a procesar
    """
    try:
        # Obtener notificaciones pendientes
        queryset = NotificacionProgramada.objects.filter(estado='pendiente')
        
        if notificacion_ids:
            queryset = queryset.filter(id__in=notificacion_ids)
        
        # Filtrar por fecha programada
        ahora = timezone.now()
        notificaciones = queryset.filter(fecha_programada__lte=ahora)
        
        total_procesadas = 0
        exitosos = 0
        fallidos = 0
        
        for notificacion in notificaciones:
            try:
                resultado = enviar_notificacion_individual(notificacion)
                
                if resultado['exitoso']:
                    exitosos += 1
                else:
                    fallidos += 1
                
                total_procesadas += 1
                
            except Exception as e:
                logger.error(f"Error procesando notificación {notificacion.id}: {str(e)}")
                fallidos += 1
                total_procesadas += 1
        
        logger.info(f"Procesadas {total_procesadas} notificaciones: {exitosos} exitosas, {fallidos} fallidas")
        
        # Actualizar métricas
        actualizar_metricas_diarias()
        
        return {
            'total_procesadas': total_procesadas,
            'exitosos': exitosos,
            'fallidos': fallidos
        }
        
    except Exception as e:
        logger.error(f"Error en procesar_notificaciones_pendientes: {str(e)}")
        return {'error': str(e)}


@shared_task
def enviar_notificacion_individual(notificacion):
    """
    Envía una notificación individual
    
    Returns:
        Dict con resultado del envío
    """
    engine = NotificationEngine()
    
    try:
        # Preparar datos de notificación
        notification_data = {
            'canal': notificacion.canal_programado,
            'destinatario': notificacion.destinatario,
            'plantilla': notificacion.plantilla,
            'contexto': notificacion.contenido_personalizado or {}
        }
        
        # Enviar notificación
        resultado = engine.send_notification(notification_data)
        
        # Actualizar estado de la notificación
        notificacion.intentos_envio += 1
        
        if resultado['exitoso']:
            notificacion.estado = 'enviada'
            notificacion.fecha_envio = timezone.now()
            notificacion.log_envio = f"Enviado exitosamente por {notificacion.canal_programado}"
        else:
            # Manejar reintentos
            if notificacion.intentos_envio < 3:
                notificacion.estado = 'pendiente'
                # Reprogramar para 30 minutos después
                notificacion.fecha_programada = timezone.now() + timedelta(minutes=30)
            else:
                notificacion.estado = 'error'
            
            notificacion.error_mensaje = resultado['mensaje']
            notificacion.log_envio = f"Error en intento {notificacion.intentos_envio}: {resultado['mensaje']}"
        
        notificacion.save()
        
        # Registrar en historial
        HistorialNotificacion.objects.create(
            notificacion_programada=notificacion,
            canal_utilizado=notificacion.canal_programado,
            contenido=resultado.get('contenido', ''),
            asunto=resultado.get('asunto', ''),
            fue_exitoso=resultado['exitoso'],
            mensaje_error=resultado.get('mensaje', ''),
            proveedor_envio=resultado.get('proveedor', ''),
            id_proveedor=resultado.get('id_proveedor', ''),
            tiempo_respuesta_ms=resultado.get('tiempo_respuesta_ms', 0)
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error enviando notificación {notificacion.id}: {str(e)}")
        
        # Marcar como error
        notificacion.estado = 'error'
        notificacion.error_mensaje = str(e)
        notificacion.save()
        
        return {
            'exitoso': False,
            'mensaje': str(e),
            'tiempo_respuesta_ms': 0,
            'id_proveedor': None
        }


@shared_task
def actualizar_metricas_diarias():
    """Actualiza las métricas diarias del sistema de notificaciones"""
    try:
        hoy = timezone.now().date()
        
        # Obtener estadísticas del día
        notificaciones_hoy = HistorialNotificacion.objects.filter(
            fecha_envio__date=hoy
        )
        
        # Calcular métricas por canal
        email_stats = notificaciones_hoy.filter(canal_utilizado='email').aggregate(
            total=models.Count('id'),
            exitosos=models.Count('id', filter=models.Q(fue_exitoso=True)),
            tiempo_promedio=models.Avg('tiempo_respuesta_ms')
        )
        
        sms_stats = notificaciones_hoy.filter(canal_utilizado='sms').aggregate(
            total=models.Count('id'),
            exitosos=models.Count('id', filter=models.Q(fue_exitoso=True)),
            tiempo_promedio=models.Avg('tiempo_respuesta_ms')
        )
        
        whatsapp_stats = notificaciones_hoy.filter(canal_utilizado='whatsapp').aggregate(
            total=models.Count('id'),
            exitosos=models.Count('id', filter=models.Q(fue_exitoso=True)),
            tiempo_promedio=models.Avg('tiempo_respuesta_ms')
        )
        
        # Calcular tasas de apertura de email
        email_abiertos = notificaciones_hoy.filter(
            canal_utilizado='email',
            fue_leido=True
        ).count()
        
        email_con_clicks = notificaciones_hoy.filter(
            canal_utilizado='email',
            clicks__gt=0
        ).count()
        
        tasa_apertura = 0.0
        tasa_clicks = 0.0
        
        if email_stats['total'] and email_stats['total'] > 0:
            tasa_apertura = (email_abiertos / email_stats['total']) * 100
            tasa_clicks = (email_con_clicks / email_stats['total']) * 100
        
        # Contar reclamos asociados a notificaciones del día
        reclamos_hoy = 0  # Aquí iría la lógica para contar reclamos
        
        # Actualizar o crear métrica del día
        metrica, created = MetricaNotificacion.objects.update_or_create(
            fecha=hoy,
            defaults={
                'total_enviadas': notificaciones_hoy.count(),
                'total_exitosas': notificaciones_hoy.filter(fue_exitoso=True).count(),
                'total_fallidas': notificaciones_hoy.filter(fue_exitoso=False).count(),
                
                'email_enviados': email_stats['total'] or 0,
                'email_exitosos': email_stats['exitosos'] or 0,
                'tiempo_promedio_email_ms': int(email_stats['tiempo_promedio'] or 0),
                
                'sms_enviados': sms_stats['total'] or 0,
                'sms_exitosos': sms_stats['exitosos'] or 0,
                'tiempo_promedio_sms_ms': int(sms_stats['tiempo_promedio'] or 0),
                
                'whatsapp_enviados': whatsapp_stats['total'] or 0,
                'whatsapp_exitosos': whatsapp_stats['exitosos'] or 0,
                'tiempo_promedio_whatsapp_ms': int(whatsapp_stats['tiempo_promedio'] or 0),
                
                'tasa_apertura_email': round(tasa_apertura, 2),
                'tasa_click_email': round(tasa_clicks, 2),
                'reclamos_asociados': reclamos_hoy,
            }
        )
        
        logger.info(f"Métricas actualizadas para {hoy}: {metrica.total_enviadas} notificaciones")
        
        return {
            'fecha': str(hoy),
            'total_enviadas': metrica.total_enviadas,
            'tasa_exito': round((metrica.total_exitosas / metrica.total_enviadas * 100), 2) if metrica.total_enviadas > 0 else 0,
            'tasa_apertura_email': tasa_apertura,
            'tasa_click_email': tasa_clicks
        }
        
    except Exception as e:
        logger.error(f"Error actualizando métricas: {str(e)}")
        return {'error': str(e)}


@shared_task
def limpiar_notificaciones_antiguas():
    """Limpia notificaciones antiguas para mantener la base de datos optimizada"""
    try:
        # Eliminar notificaciones programadas canceladas/expiradas de más de 30 días
        fecha_limite = timezone.now() - timedelta(days=30)
        
        notificaciones_eliminadas = NotificacionProgramada.objects.filter(
            estado__in=['cancelada', 'expirada'],
            actualizado_en__lt=fecha_limite
        ).delete()
        
        # Eliminar historial de notificaciones de más de 90 días
        historial_eliminado = HistorialNotificacion.objects.filter(
            fecha_envio__lt=fecha_limite - timedelta(days=60)
        ).delete()
        
        logger.info(f"Limpieza completada: {notificaciones_eliminadas[0]} notificaciones, {historial_eliminado[0]} registros de historial")
        
        return {
            'notificaciones_eliminadas': notificaciones_eliminadas[0],
            'historial_eliminado': historial_eliminado[0]
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de notificaciones: {str(e)}")
        return {'error': str(e)}


@shared_task
def enviar_notificaciones_urgentes():
    """Procesa notificaciones urgentes inmediatamente"""
    try:
        # Obtener notificaciones urgentes pendientes
        urgentes = NotificacionProgramada.objects.filter(
            estado='pendiente',
            plantilla__es_urgente=True,
            fecha_programada__lte=timezone.now()
        ).order_by('-prioridad', 'fecha_programada')
        
        total_enviadas = 0
        
        for notificacion in urgentes:
            try:
                resultado = enviar_notificacion_individual(notificacion)
                if resultado['exitoso']:
                    total_enviadas += 1
            except Exception as e:
                logger.error(f"Error enviando notificación urgente {notificacion.id}: {str(e)}")
        
        logger.info(f"Procesadas {total_enviadas} notificaciones urgentes")
        
        return {'total_enviadas': total_enviadas}
        
    except Exception as e:
        logger.error(f"Error procesando notificaciones urgentes: {str(e)}")
        return {'error': str(e)}