from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Paquete, HistorialPaquete
from notificaciones_mejoradas.models import PlantillaNotificacion, NotificacionProgramada
from notificaciones_mejoradas.services import NotificationEngine

@receiver(post_save, sender=HistorialPaquete)
def notificar_cambio_estado_paquete(sender, instance, created, **kwargs):
    """
    Enviar notificación cuando cambia el estado de un paquete
    """
    if not created:
        return
    
    paquete = instance.paquete
    
    # Determinar el tipo de notificación basado en el estado
    tipo_notificacion = f'paquete_{instance.estado_nuevo}'
    
    # Obtener plantilla de notificación
    try:
        plantilla = PlantillaNotificacion.objects.get(
            tipo=tipo_notificacion,
            esta_activa=True
        )
    except PlantillaNotificacion.DoesNotExist:
        # Crear plantilla por defecto si no existe
        plantilla = crear_plantilla_por_defecto(tipo_notificacion)
    
    # Preparar contexto para el mensaje
    contexto = {
        'codigo_seguimiento': paquete.codigo_seguimiento,
        'estado_anterior': instance.get_estado_anterior_display(),
        'estado_nuevo': instance.get_estado_nuevo_display(),
        'ubicacion': instance.ubicacion or 'No especificada',
        'observacion': instance.observacion or 'Sin observaciones',
        'fecha_cambio': instance.fecha_cambio,
        'nombre_destinatario': paquete.destinatario.nombre_completo,
        'direccion_destinatario': paquete.destinatario.direccion,
        'comuna_destinatario': paquete.destinatario.comuna,
        'nombre_remitente': paquete.remitente.nombre_completo,
        'fecha_estimada_entrega': paquete.fecha_estimada_entrega,
        'descripcion_contenido': paquete.descripcion_contenido,
    }
    
    # Inicializar el motor de notificaciones
    notification_engine = NotificationEngine()
    
    # Enviar notificación al destinatario
    if paquete.destinatario.email:
        notification_data = {
            'canal': 'email',
            'destinatario': paquete.destinatario,
            'plantilla': plantilla,
            'contexto': contexto
        }
        resultado = notification_engine.send_notification(notification_data)
        if not resultado['exitoso']:
            print(f"Error enviando notificación al destinatario: {resultado['mensaje']}")
    
    # Enviar notificación al remitente
    if paquete.remitente.email:
        notification_data = {
            'canal': 'email',
            'destinatario': paquete.remitente,
            'plantilla': plantilla,
            'contexto': contexto
        }
        resultado = notification_engine.send_notification(notification_data)
        if not resultado['exitoso']:
            print(f"Error enviando notificación al remitente: {resultado['mensaje']}")
    
    # Enviar notificación SMS si está configurado
    if paquete.destinatario.telefono:
        notification_data = {
            'canal': 'sms',
            'destinatario': paquete.destinatario,
            'plantilla': plantilla,
            'contexto': contexto
        }
        resultado = notification_engine.send_notification(notification_data)
        if not resultado['exitoso']:
            print(f"Error enviando SMS: {resultado['mensaje']}")

def crear_plantilla_por_defecto(tipo_notificacion):
    """Crear plantilla de notificación por defecto"""
    
    plantillas_por_defecto = {
        'paquete_registrado': {
            'nombre': 'Paquete Registrado',
            'asunto': 'Tu paquete ha sido registrado - CorreosChile',
            'contenido': '''
                <h2>¡Tu paquete ha sido registrado!</h2>
                <p><strong>Código de seguimiento:</strong> {{ codigo_seguimiento }}</p>
                <p><strong>Estado:</strong> {{ estado_nuevo }}</p>
                <p><strong>Contenido:</strong> {{ descripcion_contenido }}</p>
                <p><strong>Destinatario:</strong> {{ nombre_destinatario }}</p>
                <p><strong>Dirección de entrega:</strong> {{ direccion_destinatario }}, {{ comuna_destinatario }}</p>
                <p><strong>Fecha estimada de entrega:</strong> {{ fecha_estimada_entrega|date:'d/m/Y' }}</p>
                <p>Puedes hacer seguimiento de tu paquete en: <a href="https://correoschile.cl/paquetes/seguimiento/?codigo={{ codigo_seguimiento }}">Seguir paquete</a></p>
            ''',
            'contenido_sms': 'Tu paquete {{ codigo_seguimiento }} ha sido registrado. Estado: {{ estado_nuevo }}. Fecha estimada: {{ fecha_estimada_entrega }}'
        },
        'paquete_en_almacen': {
            'nombre': 'Paquete en Almacén',
            'asunto': 'Tu paquete está en almacén - CorreosChile',
            'contenido': '''
                <h2>Tu paquete está en nuestro almacén</h2>
                <p><strong>Código de seguimiento:</strong> {{ codigo_seguimiento }}</p>
                <p><strong>Estado:</strong> {{ estado_nuevo }}</p>
                <p><strong>Ubicación:</strong> {{ ubicacion }}</p>
                <p><strong>Observaciones:</strong> {{ observacion }}</p>
                <p>Puedes hacer seguimiento de tu paquete en: <a href="https://correoschile.cl/paquetes/seguimiento/?codigo={{ codigo_seguimiento }}">Seguir paquete</a></p>
            ''',
            'contenido_sms': 'Tu paquete {{ codigo_seguimiento }} está en almacén. Ubicación: {{ ubicacion }}'
        },
        'paquete_en_transito': {
            'nombre': 'Paquete en Tránsito',
            'asunto': 'Tu paquete está en tránsito - CorreosChile',
            'contenido': '''
                <h2>¡Tu paquete está en camino!</h2>
                <p><strong>Código de seguimiento:</strong> {{ codigo_seguimiento }}</p>
                <p><strong>Estado:</strong> {{ estado_nuevo }}</p>
                <p><strong>Ubicación:</strong> {{ ubicacion }}</p>
                <p><strong>Observaciones:</strong> {{ observacion }}</p>
                <p>Puedes hacer seguimiento de tu paquete en: <a href="https://correoschile.cl/paquetes/seguimiento/?codigo={{ codigo_seguimiento }}">Seguir paquete</a></p>
            ''',
            'contenido_sms': 'Tu paquete {{ codigo_seguimiento }} está en tránsito. Ubicación: {{ ubicacion }}'
        },
        'paquete_en_reparto': {
            'nombre': 'Paquete en Reparto',
            'asunto': 'Tu paquete está en reparto - CorreosChile',
            'contenido': '''
                <h2>¡Tu paquete está en reparto!</h2>
                <p><strong>Código de seguimiento:</strong> {{ codigo_seguimiento }}</p>
                <p><strong>Estado:</strong> {{ estado_nuevo }}</p>
                <p><strong>Ubicación:</strong> {{ ubicacion }}</p>
                <p><strong>Destinatario:</strong> {{ nombre_destinatario }}</p>
                <p><strong>Dirección de entrega:</strong> {{ direccion_destinatario }}, {{ comuna_destinatario }}</p>
                <p><strong>Horario preferido:</strong> {{ horario_preferido|default:'No especificado' }}</p>
                <p>¡Estaremos contigo pronto! Asegúrate de estar disponible para recibir el paquete.</p>
            ''',
            'contenido_sms': 'Tu paquete {{ codigo_seguimiento }} está en reparto. Asegúrate de estar disponible en {{ direccion_destinatario }}'
        },
        'paquete_entregado': {
            'nombre': 'Paquete Entregado',
            'asunto': 'Tu paquete ha sido entregado - CorreosChile',
            'contenido': '''
                <h2>¡Tu paquete ha sido entregado!</h2>
                <p><strong>Código de seguimiento:</strong> {{ codigo_seguimiento }}</p>
                <p><strong>Estado:</strong> {{ estado_nuevo }}</p>
                <p><strong>Entregado a:</strong> {{ nombre_destinatario }}</p>
                <p><strong>Fecha de entrega:</strong> {{ fecha_cambio|date:'d/m/Y H:i' }}</p>
                <p><strong>Observaciones:</strong> {{ observacion }}</p>
                <p>¡Gracias por confiar en CorreosChile!</p>
            ''',
            'contenido_sms': 'Tu paquete {{ codigo_seguimiento }} ha sido entregado. ¡Gracias por confiar en CorreosChile!'
        },
        'paquete_entrega_fallida': {
            'nombre': 'Entrega Fallida',
            'asunto': 'Entrega fallida - CorreosChile',
            'contenido': '''
                <h2>Entrega fallida</h2>
                <p><strong>Código de seguimiento:</strong> {{ codigo_seguimiento }}</p>
                <p><strong>Estado:</strong> {{ estado_nuevo }}</p>
                <p><strong>Ubicación:</strong> {{ ubicacion }}</p>
                <p><strong>Observaciones:</strong> {{ observacion }}</p>
                <p>Intentaremos nuevamente la entrega. Por favor, contáctanos si necesitas reprogramar la entrega.</p>
                <p>Teléfono: 600 600 2020</p>
            ''',
            'contenido_sms': 'Entrega fallida para paquete {{ codigo_seguimiento }}. Contactanos: 600 600 2020'
        }
    }
    
    if tipo_notificacion in plantillas_por_defecto:
        datos = plantillas_por_defecto[tipo_notificacion]
        return PlantillaNotificacion.objects.create(
            tipo=tipo_notificacion,
            nombre=datos['nombre'],
            asunto_email=datos['asunto'],
            template_email_html=datos['contenido'],
            template_sms=datos.get('contenido_sms', ''),
            esta_activa=True,
            variables_disponibles='codigo_seguimiento,estado_anterior,estado_nuevo,ubicacion,observacion'
        )
    else:
        # Plantilla genérica por defecto
        return PlantillaNotificacion.objects.create(
            tipo=tipo_notificacion,
            nombre=f'Notificación {tipo_notificacion}',
            asunto_email=f'Actualización de paquete - CorreosChile',
            template_email_html=f'''
                <h2>Actualización de paquete</h2>
                <p><strong>Código de seguimiento:</strong> {{ codigo_seguimiento }}</p>
                <p><strong>Estado anterior:</strong> {{ estado_anterior }}</p>
                <p><strong>Nuevo estado:</strong> {{ estado_nuevo }}</p>
                <p><strong>Ubicación:</strong> {{ ubicacion }}</p>
                <p><strong>Observaciones:</strong> {{ observacion }}</p>
            ''',
            template_sms='Tu paquete {{ codigo_seguimiento }} cambió de {{ estado_anterior }} a {{ estado_nuevo }}',
            esta_activa=True,
            variables_disponibles='codigo_seguimiento,estado_anterior,estado_nuevo,ubicacion,observacion'
        )