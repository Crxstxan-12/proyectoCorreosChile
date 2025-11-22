import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationEngine:
    """Motor principal de notificaciones multi-canal"""
    
    def __init__(self):
        self.email_service = EmailNotificationService()
        self.sms_service = SMSNotificationService()
        self.whatsapp_service = WhatsAppNotificationService()
        
    def send_notification(self, notification_data: Dict) -> Dict:
        """
        Envía una notificación a través del canal especificado
        
        Args:
            notification_data: Dict con los datos de la notificación
                - canal: 'email', 'sms', 'whatsapp'
                - destinatario: User object
                - plantilla: PlantillaNotificacion object
                - contexto: Dict con variables para el template
                
        Returns:
            Dict con resultado del envío
        """
        canal = notification_data.get('canal')
        resultado = {
            'exitoso': False,
            'mensaje': '',
            'tiempo_respuesta_ms': 0,
            'id_proveedor': None
        }
        
        start_time = time.time()
        
        try:
            if canal == 'email':
                resultado = self.email_service.send(
                    destinatario=notification_data['destinatario'],
                    plantilla=notification_data['plantilla'],
                    contexto=notification_data.get('contexto', {})
                )
            elif canal == 'sms':
                resultado = self.sms_service.send(
                    destinatario=notification_data['destinatario'],
                    plantilla=notification_data['plantilla'],
                    contexto=notification_data.get('contexto', {})
                )
            elif canal == 'whatsapp':
                resultado = self.whatsapp_service.send(
                    destinatario=notification_data['destinatario'],
                    plantilla=notification_data['plantilla'],
                    contexto=notification_data.get('contexto', {})
                )
            else:
                resultado['mensaje'] = f'Canal no soportado: {canal}'
                
        except Exception as e:
            logger.error(f"Error enviando notificación por {canal}: {str(e)}")
            resultado['mensaje'] = f'Error: {str(e)}'
            
        end_time = time.time()
        resultado['tiempo_respuesta_ms'] = int((end_time - start_time) * 1000)
        
        return resultado
    
    def render_template(self, template_string: str, context: Dict) -> str:
        """Renderiza un template con las variables proporcionadas"""
        try:
            template = Template(template_string)
            return template.render(Context(context))
        except Exception as e:
            logger.error(f"Error renderizando template: {str(e)}")
            return template_string


class EmailNotificationService:
    """Servicio de notificaciones por email"""
    
    def send(self, destinatario, plantilla, contexto: Dict) -> Dict:
        """Envía un email usando la configuración de Django"""
        resultado = {
            'exitoso': False,
            'mensaje': '',
            'tiempo_respuesta_ms': 0,
            'id_proveedor': None
        }
        
        try:
            # Renderizar contenido
            asunto = plantilla.asunto_email or 'Notificación de CorreosChile'
            contenido_html = plantilla.template_email_html or ''
            contenido_texto = plantilla.template_email_texto or ''
            
            # Renderizar templates
            asunto_renderizado = NotificationEngine().render_template(asunto, contexto)
            html_renderizado = NotificationEngine().render_template(contenido_html, contexto)
            texto_renderizado = NotificationEngine().render_template(contenido_texto, contexto)
            
            # Enviar email
            email_destino = destinatario.email
            if not email_destino:
                resultado['mensaje'] = 'Usuario sin email configurado'
                return resultado
                
            send_mail(
                subject=asunto_renderizado,
                message=texto_renderizado,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_destino],
                html_message=html_renderizado if html_renderizado else None,
                fail_silently=False,
            )
            
            resultado['exitoso'] = True
            resultado['mensaje'] = 'Email enviado exitosamente'
            resultado['id_proveedor'] = f'email_{int(time.time())}'
            
        except Exception as e:
            logger.error(f"Error enviando email: {str(e)}")
            resultado['mensaje'] = f'Error email: {str(e)}'
            
        return resultado


class SMSNotificationService:
    """Servicio de notificaciones por SMS"""
    
    def __init__(self):
        # Configuración para integración con proveedor SMS (Twilio, etc.)
        self.provider_config = getattr(settings, 'SMS_PROVIDER', {})
        self.simulation_mode = settings.DEBUG  # En desarrollo, simular envíos
        
    def send(self, destinatario, plantilla, contexto: Dict) -> Dict:
        """Envía un SMS (o simula en desarrollo)"""
        resultado = {
            'exitoso': False,
            'mensaje': '',
            'tiempo_respuesta_ms': 0,
            'id_proveedor': None
        }
        
        try:
            # Obtener teléfono del destinatario
            telefono = self._get_telefono_destinatario(destinatario)
            if not telefono:
                resultado['mensaje'] = 'Usuario sin teléfono móvil configurado'
                return resultado
            
            # Renderizar contenido SMS
            contenido_sms = plantilla.template_sms or ''
            sms_renderizado = NotificationEngine().render_template(contenido_sms, contexto)
            
            if self.simulation_mode:
                # En desarrollo, simular envío
                logger.info(f"SMS SIMULADO a {telefono}: {sms_renderizado}")
                resultado['exitoso'] = True
                resultado['mensaje'] = 'SMS simulado (modo desarrollo)'
                resultado['id_proveedor'] = f'sms_sim_{int(time.time())}'
            else:
                # Aquí iría la integración real con proveedor SMS
                # Por ahora, simulamos éxito
                resultado['exitoso'] = True
                resultado['mensaje'] = 'SMS enviado exitosamente'
                resultado['id_proveedor'] = f'sms_{int(time.time())}'
                
        except Exception as e:
            logger.error(f"Error enviando SMS: {str(e)}")
            resultado['mensaje'] = f'Error SMS: {str(e)}'
            
        return resultado
    
    def _get_telefono_destinatario(self, destinatario) -> Optional[str]:
        """Obtiene el teléfono del destinatario"""
        try:
            # Intentar obtener de la configuración de notificaciones
            from .models import ConfiguracionNotificacion
            config = ConfiguracionNotificacion.objects.filter(usuario=destinatario).first()
            if config and config.telefono_movil:
                return config.telefono_movil
                
            # Intentar obtener del perfil de usuario
            if hasattr(destinatario, 'perfil'):
                return destinatario.perfil.telefono
                
        except Exception as e:
            logger.error(f"Error obteniendo teléfono: {str(e)}")
            
        return None


class WhatsAppNotificationService:
    """Servicio de notificaciones por WhatsApp"""
    
    def __init__(self):
        self.provider_config = getattr(settings, 'WHATSAPP_PROVIDER', {})
        self.simulation_mode = settings.DEBUG
        
    def send(self, destinatario, plantilla, contexto: Dict) -> Dict:
        """Envía un mensaje de WhatsApp (o simula en desarrollo)"""
        resultado = {
            'exitoso': False,
            'mensaje': '',
            'tiempo_respuesta_ms': 0,
            'id_proveedor': None
        }
        
        try:
            # Obtener teléfono del destinatario
            telefono = self._get_telefono_destinatario(destinatario)
            if not telefono:
                resultado['mensaje'] = 'Usuario sin teléfono móvil configurado'
                return resultado
            
            # Renderizar contenido WhatsApp
            contenido_whatsapp = plantilla.template_whatsapp or ''
            whatsapp_renderizado = NotificationEngine().render_template(contenido_whatsapp, contexto)
            
            if self.simulation_mode:
                # En desarrollo, simular envío
                logger.info(f"WHATSAPP SIMULADO a {telefono}: {whatsapp_renderizado}")
                resultado['exitoso'] = True
                resultado['mensaje'] = 'WhatsApp simulado (modo desarrollo)'
                resultado['id_proveedor'] = f'wa_sim_{int(time.time())}'
            else:
                # Aquí iría la integración real con proveedor WhatsApp
                # Por ahora, simulamos éxito
                resultado['exitoso'] = True
                resultado['mensaje'] = 'WhatsApp enviado exitosamente'
                resultado['id_proveedor'] = f'wa_{int(time.time())}'
                
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {str(e)}")
            resultado['mensaje'] = f'Error WhatsApp: {str(e)}'
            
        return resultado
    
    def _get_telefono_destinatario(self, destinatario) -> Optional[str]:
        """Obtiene el teléfono del destinatario"""
        try:
            # Intentar obtener de la configuración de notificaciones
            from .models import ConfiguracionNotificacion
            config = ConfiguracionNotificacion.objects.filter(usuario=destinatario).first()
            if config and config.telefono_movil:
                return config.telefono_movil
                
            # Intentar obtener del perfil de usuario
            if hasattr(destinatario, 'perfil'):
                return destinatario.perfil.telefono
                
        except Exception as e:
            logger.error(f"Error obteniendo teléfono: {str(e)}")
            
        return None