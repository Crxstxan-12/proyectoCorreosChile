from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from envios.models import Envio
from notificaciones.models import Notificacion
from .models import PlantillaNotificacion, NotificacionProgramada, ConfiguracionNotificacion
from .services import NotificationEngine


@receiver(post_save, sender=Envio)
def crear_notificacion_cambio_estado(sender, instance, created, **kwargs):
    """
    Crea notificaciones automáticas cuando cambia el estado de un envío
    """
    if created:
        # Notificación de envío creado
        programar_notificacion_envio_creado(instance)
    else:
        # Detectar cambio de estado
        if hasattr(instance, '_estado_anterior') and instance.estado != instance._estado_anterior:
            manejar_cambio_estado_envio(instance)


def programar_notificacion_envio_creado(envio):
    """Programa notificación cuando se crea un nuevo envío"""
    try:
        plantilla = PlantillaNotificacion.objects.get(tipo='envio_creado', esta_activa=True)
        
        # Obtener usuarios relacionados con el envío
        usuarios_notificar = obtener_usuarios_para_envio(envio)
        
        for usuario in usuarios_notificar:
            # Verificar configuración de notificaciones
            config = ConfiguracionNotificacion.objects.filter(usuario=usuario, esta_activa=True).first()
            if not config:
                continue
                
            # Determinar canal preferido
            canal = determinar_canal_preferido(config)
            
            # Programar notificación
            NotificacionProgramada.objects.create(
                envio=envio,
                plantilla=plantilla,
                destinatario=usuario,
                email_destino=usuario.email if canal == 'email' else None,
                telefono_destino=config.telefono_movil if canal in ['sms', 'whatsapp'] else None,
                canal_programado=canal,
                fecha_programada=timezone.now(),  # Enviar inmediatamente
                contenido_personalizado={
                    'cliente_nombre': envio.destinatario_nombre,
                    'numero_envio': envio.codigo,
                    'direccion': envio.direccion_destino,
                    'fecha_estimada': (getattr(envio, 'fecha_estimada_entrega', None).isoformat() if getattr(envio, 'fecha_estimada_entrega', None) else None)
                }
            )
            
    except PlantillaNotificacion.DoesNotExist:
        pass


def manejar_cambio_estado_envio(envio):
    """Maneja el cambio de estado de un envío"""
    mapeo_estados_plantillas = {
        'en_transito': 'envio_en_transito',
        'en_reparto': 'envio_en_reparto',
        'entregado': 'envio_entregado',
        'demorado': 'envio_demorado',
        'en_sucursal': 'envio_en_sucursal',
    }
    
    tipo_plantilla = mapeo_estados_plantillas.get(envio.estado)
    if not tipo_plantilla:
        return
        
    try:
        plantilla = PlantillaNotificacion.objects.get(tipo=tipo_plantilla, esta_activa=True)
        
        # Calcular timing según tipo de notificación
        fecha_envio = calcular_fecha_envio_notificacion(envio, tipo_plantilla)
        
        # Obtener usuarios para notificar
        usuarios_notificar = obtener_usuarios_para_envio(envio)
        
        for usuario in usuarios_notificar:
            config = ConfiguracionNotificacion.objects.filter(usuario=usuario, esta_activa=True).first()
            if not config:
                continue
                
            canal = determinar_canal_preferido(config)
            
            # Crear notificación programada
            NotificacionProgramada.objects.create(
                envio=envio,
                plantilla=plantilla,
                destinatario=usuario,
                email_destino=usuario.email if canal == 'email' else None,
                telefono_destino=config.telefono_movil if canal in ['sms', 'whatsapp'] else None,
                canal_programado=canal,
                fecha_programada=fecha_envio,
                contenido_personalizado=generar_contexto_notificacion(envio, tipo_plantilla)
            )
            
    except PlantillaNotificacion.DoesNotExist:
        pass


def calcular_fecha_envio_notificacion(envio, tipo_plantilla):
    """Calcula la fecha óptima para enviar una notificación"""
    ahora = timezone.now()
    
    # Notificaciones urgentes se envían inmediatamente
    if tipo_plantilla in PlantillaNotificacion.CATEGORIAS_URGENTES:
        return ahora
    
    # Notificaciones normales se envían en horario hábil (8:00 - 20:00)
    if ahora.hour < 8:
        # Antes de las 8:00, programar para las 8:00
        return ahora.replace(hour=8, minute=0, second=0)
    elif ahora.hour > 20:
        # Después de las 20:00, programar para mañana a las 8:00
        manana = ahora + timedelta(days=1)
        return manana.replace(hour=8, minute=0, second=0)
    else:
        # En horario hábil, enviar inmediatamente
        return ahora


def obtener_usuarios_para_envio(envio):
    """Obtiene los usuarios que deben ser notificados sobre un envío"""
    usuarios = []
    
    # Usuario propietario del envío (si existe)
    if envio.usuario:
        usuarios.append(envio.usuario)
    
    # Usuarios relacionados con el destinatario (cliente final)
    # Aquí podrías agregar lógica para notificar también al destinatario
    # si tiene cuenta en el sistema
    
    return usuarios


def determinar_canal_preferido(config):
    """Determina el canal preferido basado en la configuración del usuario"""
    if config.canal_whatsapp:
        return 'whatsapp'
    elif config.canal_sms:
        return 'sms'
    elif config.canal_email:
        return 'email'
    else:
        return 'email'  # Email por defecto


def generar_contexto_notificacion(envio, tipo_plantilla):
    """Genera el contexto de datos para renderizar la notificación"""
    contexto = {
        'cliente_nombre': envio.destinatario_nombre,
        'numero_envio': envio.codigo,
        'direccion': envio.direccion_destino,
        'fecha_estimada': (getattr(envio, 'fecha_estimada_entrega', None).isoformat() if getattr(envio, 'fecha_estimada_entrega', None) else None),
        'estado_actual': envio.get_estado_display(),
        'ubicacion_actual': getattr(envio, 'ubicacion_actual', 'No disponible'),
    }
    
    # Agregar información específica según el tipo de notificación
    if tipo_plantilla == 'envio_en_reparto':
        contexto['mensaje_urgente'] = '¡Tu envío está en camino!'
        contexto['hora_estimada'] = calcular_hora_estimada_entrega(envio)
    elif tipo_plantilla == 'envio_demorado':
        contexto['razon_demora'] = getattr(envio, 'razon_demora', 'Motivo no especificado')
        contexto['nueva_fecha_estimada'] = calcular_nueva_fecha_estimada(envio)
    elif tipo_plantilla == 'envio_entregado':
        contexto['fecha_entrega'] = envio.fecha_entrega.isoformat() if envio.fecha_entrega else None
        contexto['persona_recibio'] = getattr(envio, 'persona_recibio', 'No registrado')
    
    return contexto


def calcular_hora_estimada_entrega(envio):
    """Calcula la hora estimada de entrega"""
    # Lógica simplificada - en producción sería más sofisticada
    if getattr(envio, 'fecha_estimada_entrega', None):
        return getattr(envio, 'fecha_estimada_entrega').strftime('%H:%M')
    return 'Entre 9:00 y 18:00'


def calcular_nueva_fecha_estimada(envio):
    """Calcula una nueva fecha estimada en caso de demora"""
    if getattr(envio, 'fecha_estimada_entrega', None):
        nueva_fecha = getattr(envio, 'fecha_estimada_entrega') + timedelta(days=1)
        return nueva_fecha.isoformat()
    return None


# Capturar estado anterior antes de guardar
@receiver(pre_save, sender=Envio)
def capturar_estado_anterior(sender, instance, **kwargs):
    if instance.pk:
        original = Envio.objects.filter(pk=instance.pk).first()
        if original:
            instance._estado_anterior = original.estado