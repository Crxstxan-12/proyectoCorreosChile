from django.core.management.base import BaseCommand
from django.db import transaction
from notificaciones_mejoradas.models import PlantillaNotificacion


class Command(BaseCommand):
    help = 'Inicializa las plantillas de notificación predeterminadas'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Inicializando plantillas de notificación...'))
        
        plantillas_data = [
            {
                'nombre': 'Envío Creado',
                'tipo': 'envio_creado',
                'prioridad': 3,
                'es_urgente': False,
                'asunto_email': 'Tu envío {{numero_envio}} ha sido creado - CorreosChile',
                'template_email_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tu envío ha sido creado</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #003366; color: white; padding: 20px; text-align: center;">
            <h1>CorreosChile</h1>
        </div>
        
        <div style="background-color: #f4f4f4; padding: 20px; margin: 20px 0;">
            <h2 style="color: #003366;">¡Hola {{cliente_nombre}}!</h2>
            <p>Tu envío <strong>{{numero_envio}}</strong> ha sido creado exitosamente.</p>
            
            <div style="background-color: white; padding: 15px; border-left: 4px solid #003366; margin: 20px 0;">
                <h3>Detalles del envío:</h3>
                <ul>
                    <li><strong>Número de envío:</strong> {{numero_envio}}</li>
                    <li><strong>Destino:</strong> {{direccion}}</li>
                    <li><strong>Estado:</strong> {{estado_actual}}</li>
                    {% if fecha_estimada %}
                    <li><strong>Fecha estimada de entrega:</strong> {{fecha_estimada}}</li>
                    {% endif %}
                </ul>
            </div>
            
            <p>Podrás hacer seguimiento de tu envío en tiempo real a través de nuestra plataforma.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #003366; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    Seguir mi envío
                </a>
            </div>
        </div>
        
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>Este es un mensaje automático de CorreosChile</p>
            <p>Si tienes dudas, contáctanos al 600 600 0000</p>
        </div>
    </div>
</body>
</html>
                ''',
                'template_email_texto': '''
Hola {{cliente_nombre}},

Tu envío {{numero_envio}} ha sido creado exitosamente.

Detalles del envío:
- Número de envío: {{numero_envio}}
- Destino: {{direccion}}
- Estado: {{estado_actual}}
{% if fecha_estimada %}- Fecha estimada de entrega: {{fecha_estimada}}{% endif %}

Podrás hacer seguimiento de tu envío en tiempo real a través de nuestra plataforma.

Para más información, visita: [LINK]

Este es un mensaje automático de CorreosChile.
Si tienes dudas, contáctanos al 600 600 0000
                ''',
                'template_sms': 'Hola {{cliente_nombre}}, tu envío {{numero_envio}} ha sido creado. Estado: {{estado_actual}}. Seguimiento: [LINK]',
                'template_whatsapp': 'Hola {{cliente_nombre}} 👋\n\nTu envío *{{numero_envio}}* ha sido creado exitosamente.\n\n📍 Destino: {{direccion}}\n📊 Estado: {{estado_actual}}\n\nPodrás seguir tu envío en tiempo real. ¿Necesitas ayuda?',
                'template_push': 'Tu envío {{numero_envio}} ha sido creado',
                'variables_disponibles': 'cliente_nombre, numero_envio, direccion, estado_actual, fecha_estimada',
                'requiere_confirmacion': False,
                'tiempo_espera_respuesta': 24,
            },
            {
                'nombre': 'Envío en Tránsito',
                'tipo': 'envio_en_transito',
                'prioridad': 5,
                'es_urgente': False,
                'asunto_email': 'Tu envío {{numero_envio}} está en tránsito - CorreosChile',
                'template_email_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tu envío está en tránsito</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #FF6600; color: white; padding: 20px; text-align: center;">
            <h1>🚚 ¡Tu envío está en camino!</h1>
        </div>
        
        <div style="background-color: #f4f4f4; padding: 20px; margin: 20px 0;">
            <h2 style="color: #FF6600;">¡Hola {{cliente_nombre}}!</h2>
            <p>Tu envío <strong>{{numero_envio}}</strong> está actualmente en tránsito hacia tu destino.</p>
            
            <div style="background-color: white; padding: 15px; border-left: 4px solid #FF6600; margin: 20px 0;">
                <h3>📍 Información actualizada:</h3>
                <ul>
                    <li><strong>Número de envío:</strong> {{numero_envio}}</li>
                    <li><strong>Estado:</strong> {{estado_actual}}</li>
                    <li><strong>Ubicación actual:</strong> {{ubicacion_actual}}</li>
                    {% if fecha_estimada %}
                    <li><strong>Fecha estimada de entrega:</strong> {{fecha_estimada}}</li>
                    {% endif %}
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #FF6600; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    Ver ubicación en tiempo real
                </a>
            </div>
        </div>
        
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>Este es un mensaje automático de CorreosChile</p>
            <p>Si tienes dudas, contáctanos al 600 600 0000</p>
        </div>
    </div>
</body>
</html>
                ''',
                'template_email_texto': '''
🚚 ¡Hola {{cliente_nombre}}!

Tu envío {{numero_envio}} está actualmente en tránsito hacia tu destino.

Información actualizada:
- Número de envío: {{numero_envio}}
- Estado: {{estado_actual}}
- Ubicación actual: {{ubicacion_actual}}
{% if fecha_estimada %}- Fecha estimada de entrega: {{fecha_estimada}}{% endif %}

Puedes ver la ubicación en tiempo real en nuestra plataforma.

Este es un mensaje automático de CorreosChile.
                ''',
                'template_sms': '🚚 {{cliente_nombre}}, tu envío {{numero_envio}} está en tránsito. Ubicación: {{ubicacion_actual}}. Sigue tu envío: [LINK]',
                'template_whatsapp': '🚚 ¡Hola {{cliente_nombre}}!\n\nTu envío *{{numero_envio}}* está en tránsito hacia tu destino.\n\n📍 Ubicación actual: *{{ubicacion_actual}}*\n📊 Estado: {{estado_actual}}\n\n¿Quieres ver la ubicación en tiempo real?',
                'template_push': '🚚 Tu envío {{numero_envio}} está en tránsito',
                'variables_disponibles': 'cliente_nombre, numero_envio, estado_actual, ubicacion_actual, fecha_estimada',
                'requiere_confirmacion': False,
                'tiempo_espera_respuesta': 24,
            },
            {
                'nombre': 'Envío en Reparto',
                'tipo': 'envio_en_reparto',
                'prioridad': 8,
                'es_urgente': True,
                'asunto_email': '⚡ Tu envío {{numero_envio}} está en reparto HOY - CorreosChile',
                'template_email_html': '''
<!DOCTYPE html>
<html>
<head>
                    <meta charset="UTF-8">
                    <title>¡Tu envío está en reparto!</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #28a745; color: white; padding: 20px; text-align: center;">
            <h1>⚡ ¡HOY ES EL DÍA!</h1>
        </div>
        
        <div style="background-color: #f4f4f4; padding: 20px; margin: 20px 0;">
            <h2 style="color: #28a745;">¡Hola {{cliente_nombre}}!</h2>
            <p><strong>¡ATENCIÓN!</strong> Tu envío <strong>{{numero_envio}}</strong> está siendo entregado <strong>HOY</strong>.</p>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>🕐 Horario estimado de entrega:</h3>
                <p style="font-size: 18px; font-weight: bold; color: #856404;">{{hora_estimada}}</p>
            </div>
            
            <div style="background-color: white; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                <h3>📍 Asegúrate de estar disponible en:</h3>
                <p><strong>{{direccion}}</strong></p>
            </div>
            
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4>💡 Consejos para la entrega:</h4>
                <ul>
                    <li>Asegúrate de tener tu cédula o documento de identidad</li>
                    <li>Si no vas a estar, deja autorizado a alguien con poder</li>
                    <li>Ten a mano el número de envío: <strong>{{numero_envio}}</strong></li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    CONFIRMAR DISPONIBILIDAD
                </a>
            </div>
        </div>
        
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p><strong>⚠️ IMPORTANTE:</strong> Si no estás disponible, responde a este mensaje o llama al 600 600 0000</p>
            <p>Este es un mensaje automático de CorreosChile</p>
        </div>
    </div>
</body>
</html>
                ''',
                'template_email_texto': '''
⚡ ¡Hola {{cliente_nombre}}!

¡ATENCIÓN! Tu envío {{numero_envio}} está siendo entregado HOY.

🕐 Horario estimado de entrega: {{hora_estimada}}

📍 Asegúrate de estar disponible en: {{direccion}}

💡 Consejos para la entrega:
- Asegúrate de tener tu cédula o documento de identidad
- Si no vas a estar, deja autorizado a alguien con poder
- Ten a mano el número de envío: {{numero_envio}}

⚠️ IMPORTANTE: Si no estás disponible, responde a este mensaje o llama al 600 600 0000

Este es un mensaje automático de CorreosChile.
                ''',
                'template_sms': '⚡ {{cliente_nombre}}, tu envío {{numero_envio}} se entrega HOY entre {{hora_estimada}}. Estarás en {{direccion}}? Confirma: 6006000000',
                'template_whatsapp': '⚡ ¡Hola {{cliente_nombre}}!\n\n*¡Tu envío {{numero_envio}} se entrega HOY!* 📦\n\n🕐 *Horario estimado:* {{hora_estimada}}\n📍 *Dirección:* {{direccion}}\n\n💡 *¿Vas a estar disponible?*\n\n✅ Responde SÍ si vas a estar\n❌ Responde NO si no vas a estar\n\n⚠️ *Importante:* Ten tu cédula a mano y recuerda el número: *{{numero_envio}}*',
                'template_push': '⚡ Tu envío {{numero_envio}} se entrega HOY entre {{hora_estimada}}',
                'variables_disponibles': 'cliente_nombre, numero_envio, direccion, hora_estimada, estado_actual',
                'requiere_confirmacion': True,
                'tiempo_espera_respuesta': 4,
            },
            {
                'nombre': 'Envío Entregado',
                'tipo': 'envio_entregado',
                'prioridad': 7,
                'es_urgente': False,
                'asunto_email': '✅ Tu envío {{numero_envio}} fue entregado exitosamente - CorreosChile',
                'template_email_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>¡Entrega exitosa!</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #28a745; color: white; padding: 20px; text-align: center;">
            <h1>✅ ¡ENTREGA EXITOSA!</h1>
        </div>
        
        <div style="background-color: #f4f4f4; padding: 20px; margin: 20px 0;">
            <h2 style="color: #28a745;">¡Hola {{cliente_nombre}}!</h2>
            <p>Tu envío <strong>{{numero_envio}}</strong> fue entregado exitosamente.</p>
            
            <div style="background-color: white; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                <h3>📋 Detalles de la entrega:</h3>
                <ul>
                    <li><strong>Número de envío:</strong> {{numero_envio}}</li>
                    <li><strong>Fecha de entrega:</strong> {{fecha_entrega}}</li>
                    <li><strong>Entregado a:</strong> {{persona_recibio}}</li>
                    <li><strong>Dirección:</strong> {{direccion}}</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    Ver comprobante de entrega
                </a>
            </div>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4>📝 ¿Tienes alguna observación?</h4>
                <p>Si tienes algún comentario sobre la entrega, por favor contáctanos.</p>
            </div>
        </div>
        
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>¡Gracias por confiar en CorreosChile!</p>
            <p>Si tienes dudas, contáctanos al 600 600 0000</p>
        </div>
    </div>
</body>
</html>
                ''',
                'template_email_texto': '''
✅ ¡Hola {{cliente_nombre}}!

¡Tu envío {{numero_envio}} fue entregado exitosamente!

📋 Detalles de la entrega:
- Número de envío: {{numero_envio}}
- Fecha de entrega: {{fecha_entrega}}
- Entregado a: {{persona_recibio}}
- Dirección: {{direccion}}

¡Gracias por confiar en CorreosChile!

Si tienes alguna observación sobre la entrega, por favor contáctanos al 600 600 0000
                ''',
                'template_sms': '✅ {{cliente_nombre}}, tu envío {{numero_envio}} fue entregado el {{fecha_entrega}} a {{persona_recibio}}. ¡Gracias por elegir CorreosChile!',
                'template_whatsapp': '✅ ¡Hola {{cliente_nombre}}!\n\n*¡Tu envío {{numero_envio}} fue entregado exitosamente!* 📦\n\n📅 *Fecha:* {{fecha_entrega}}\n👤 *Entregado a:* {{persona_recibio}}\n📍 *Dirección:* {{direccion}}\n\n¡Gracias por confiar en *CorreosChile*! 🙏\n\n¿Tienes alguna observación? Escríbenos.',
                'template_push': '✅ Tu envío {{numero_envio}} fue entregado exitosamente',
                'variables_disponibles': 'cliente_nombre, numero_envio, direccion, fecha_entrega, persona_recibio',
                'requiere_confirmacion': False,
                'tiempo_espera_respuesta': 24,
            },
            {
                'nombre': 'Envío Demorado',
                'tipo': 'envio_demorado',
                'prioridad': 9,
                'es_urgente': True,
                'asunto_email': '⚠️ Actualización sobre tu envío {{numero_envio}} - CorreosChile',
                'template_email_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Actualización sobre tu envío</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #dc3545; color: white; padding: 20px; text-align: center;">
            <h1>⚠️ ACTUALIZACIÓN IMPORTANTE</h1>
        </div>
        
        <div style="background-color: #f4f4f4; padding: 20px; margin: 20px 0;">
            <h2 style="color: #dc3545;">¡Hola {{cliente_nombre}}!</h2>
            <p>Lamentamos informarte que tu envío <strong>{{numero_envio}}</strong> ha experimentado una demora.</p>
            
            <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>ℹ️ Razón de la demora:</h3>
                <p style="color: #721c24;">{{razon_demora}}</p>
            </div>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>📅 Nueva fecha estimada de entrega:</h3>
                <p style="font-size: 18px; font-weight: bold; color: #856404;">{{nueva_fecha_estimada}}</p>
            </div>
            
            <div style="background-color: white; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0;">
                <h3>📍 Información actualizada:</h3>
                <ul>
                    <li><strong>Número de envío:</strong> {{numero_envio}}</li>
                    <li><strong>Estado actual:</strong> {{estado_actual}}</li>
                    <li><strong>Última ubicación:</strong> {{ubicacion_actual}}</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    Ver detalles actualizados
                </a>
            </div>
            
            <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4>🙏 Pedimos disculpas</h4>
                <p>Entendemos lo frustrante que puede ser una demora. Estamos trabajando arduamente para resolver la situación y entregar tu envío lo antes posible.</p>
            </div>
        </div>
        
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>¿Tienes dudas? Contáctanos al 600 600 0000</p>
            <p>Este es un mensaje automático de CorreosChile</p>
        </div>
    </div>
</body>
</html>
                ''',
                'template_email_texto': '''
⚠️ ¡Hola {{cliente_nombre}}!

Lamentamos informarte que tu envío {{numero_envio}} ha experimentado una demora.

ℹ️ Razón de la demora: {{razon_demora}}

📅 Nueva fecha estimada de entrega: {{nueva_fecha_estimada}}

📍 Información actualizada:
- Número de envío: {{numero_envio}}
- Estado actual: {{estado_actual}}
- Última ubicación: {{ubicacion_actual}}

🙏 Pedimos disculpas por la demora. Estamos trabajando arduamente para resolver la situación y entregar tu envío lo antes posible.

¿Tienes dudas? Contáctanos al 600 600 0000
                ''',
                'template_sms': '⚠️ {{cliente_nombre}}, tu envío {{numero_envio}} está demorado. Nueva fecha: {{nueva_fecha_estimada}}. Razón: {{razon_demora}}. Info: 6006000000',
                'template_whatsapp': '⚠️ ¡Hola {{cliente_nombre}}!\n\n*Tu envío {{numero_envio}} ha experimentado una demora* 😔\n\nℹ️ *Razón:* {{razon_demora}}\n📅 *Nueva fecha estimada:* {{nueva_fecha_estimada}}\n\n📍 *Estado actual:* {{estado_actual}}\n📍 *Última ubicación:* {{ubicacion_actual}}\n\n🙏 *Pedimos disculpas* por la demora. Estamos trabajando para entregar tu envío lo antes posible.\n\n¿Necesitas más información? Escríbenos.',
                'template_push': '⚠️ Tu envío {{numero_envio}} está demorado. Nueva fecha: {{nueva_fecha_estimada}}',
                'variables_disponibles': 'cliente_nombre, numero_envio, estado_actual, ubicacion_actual, razon_demora, nueva_fecha_estimada',
                'requiere_confirmacion': False,
                'tiempo_espera_respuesta': 24,
            },
            {
                'nombre': 'Recordatorio de Entrega',
                'tipo': 'recordatorio_entrega',
                'prioridad': 8,
                'es_urgente': True,
                'asunto_email': '🔔 Recordatorio: Tu envío {{numero_envio}} llega mañana - CorreosChile',
                'template_email_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Recordatorio de entrega</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #17a2b8; color: white; padding: 20px; text-align: center;">
            <h1>🔔 RECORDATORIO IMPORTANTE</h1>
        </div>
        
        <div style="background-color: #f4f4f4; padding: 20px; margin: 20px 0;">
            <h2 style="color: #17a2b8;">¡Hola {{cliente_nombre}}!</h2>
            <p>Este es un recordatorio de que tu envío <strong>{{numero_envio}}</strong> está programado para entregarse <strong>MAÑANA</strong>.</p>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>🕐 Horario estimado de entrega mañana:</h3>
                <p style="font-size: 18px; font-weight: bold; color: #856404;">{{hora_estimada}}</p>
            </div>
            
            <div style="background-color: white; padding: 15px; border-left: 4px solid #17a2b8; margin: 20px 0;">
                <h3>📍 Dirección de entrega:</h3>
                <p><strong>{{direccion}}</strong></p>
            </div>
            
            <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4>💡 ¿No vas a estar disponible?</h4>
                <p>Si no podrás recibir el envío, por favor:</p>
                <ul>
                    <li>Deja autorizado a alguien con poder</li>
                    <li>Contáctanos para reprogramar la entrega</li>
                    <li>Responde a este mensaje con "NO"</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin-right: 10px;">
                    CONFIRMAR DISPONIBILIDAD
                </a>
                <a href="#" style="background-color: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    REPROGRAMAR
                </a>
            </div>
        </div>
        
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>🔔 Este es un recordatorio automático de CorreosChile</p>
            <p>Si tienes dudas, contáctanos al 600 600 0000</p>
        </div>
    </div>
</body>
</html>
                ''',
                'template_email_texto': '''
🔔 ¡Hola {{cliente_nombre}}!

Este es un recordatorio de que tu envío {{numero_envio}} está programado para entregarse MAÑANA.

🕐 Horario estimado de entrega mañana: {{hora_estimada}}

📍 Dirección de entrega: {{direccion}}

💡 ¿No vas a estar disponible?
Si no podrás recibir el envío, por favor:
- Deja autorizado a alguien con poder
- Contáctanos para reprogramar la entrega
- Responde a este mensaje con "NO"

🔔 Este es un recordatorio automático de CorreosChile.

Si tienes dudas, contáctanos al 600 600 0000
                ''',
                'template_sms': '🔔 {{cliente_nombre}}, recuerda que tu envío {{numero_envio}} llega MAÑANA entre {{hora_estimada}}. ¿Estarás en {{direccion}}? Confirma: 6006000000',
                'template_whatsapp': '🔔 ¡Hola {{cliente_nombre}}!\n\n*Recordatorio:* Tu envío {{numero_envio}} se entrega *MAÑANA* 📅\n\n🕐 *Horario estimado:* {{hora_estimada}}\n📍 *Dirección:* {{direccion}}\n\n💡 *¿Vas a estar disponible?*\n\n✅ Responde SÍ si vas a estar\n❌ Responde NO si no vas a estar\n\n📞 ¿Dudas? Llámanos al 600 600 0000',
                'template_push': '🔔 Recuerda: Tu envío {{numero_envio}} llega MAÑANA entre {{hora_estimada}}',
                'variables_disponibles': 'cliente_nombre, numero_envio, direccion, hora_estimada, estado_actual',
                'requiere_confirmacion': True,
                'tiempo_espera_respuesta': 12,
            },
        ]
        
        with transaction.atomic():
            for plantilla_data in plantillas_data:
                plantilla, created = PlantillaNotificacion.objects.update_or_create(
                    tipo=plantilla_data['tipo'],
                    defaults=plantilla_data
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✅ Creada plantilla: {plantilla.nombre}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'🔄 Actualizada plantilla: {plantilla.nombre}'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Plantillas de notificación inicializadas exitosamente!'))
        self.stdout.write(self.style.SUCCESS('Ahora puedes personalizar los mensajes desde el administrador de Django.'))