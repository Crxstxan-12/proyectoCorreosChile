import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'correoschile.settings')
django.setup()

from django.contrib.auth.models import User
from notificaciones_mejoradas.models import PlantillaNotificacion, ConfiguracionNotificacion, NotificacionProgramada
from notificaciones_mejoradas.services import NotificationEngine
from notificaciones.models import Notificacion
from envios.models import Envio

u = User.objects.filter(username='testuser').first() or User.objects.filter(username='admin').first()
if u is None:
    u = User.objects.create_user(username='testuser', email='test@example.com', password='test123')

tpl, _ = PlantillaNotificacion.objects.get_or_create(
    tipo='envio_en_reparto',
    defaults={
        'nombre': 'Envío en Reparto',
        'asunto_email': 'Tu envío {{numero_envio}} está en reparto',
        'template_email_texto': 'Hola {{cliente_nombre}}, tu envío {{numero_envio}} está en reparto hacia {{direccion}}.',
        'template_sms': 'Hola {{cliente_nombre}}, tu envío {{numero_envio}} está en reparto hacia {{direccion}}.',
        'variables_disponibles': '{{cliente_nombre}}, {{numero_envio}}, {{direccion}}',
        'prioridad': 8,
        'es_urgente': True,
        'esta_activa': True,
    }
)

cfg, _ = ConfiguracionNotificacion.objects.get_or_create(
    usuario=u,
    defaults={'canal_sms': True, 'esta_activa': True, 'telefono_movil': '+56911111111'}
)
cfg.canal_sms = True
if not cfg.telefono_movil:
    cfg.telefono_movil = '+56911111111'
cfg.esta_activa = True
cfg.save()

e = Envio.objects.filter(codigo='TEST-NOTIF-LOGIN-001').first()
if not e:
    e = Envio.objects.create(
        codigo='TEST-NOTIF-LOGIN-001',
        estado='en_transito',
        origen='Santiago',
        destino='Providencia',
        destinatario_nombre='Cliente Demo',
        direccion_destino='Av. Providencia 123',
        usuario=u,
    )

np = NotificacionProgramada.objects.create(
    envio=e,
    plantilla=tpl,
    destinatario=u,
    telefono_destino=cfg.telefono_movil,
    canal_programado='sms',
    fecha_programada=timezone.now(),
    contenido_personalizado={
        'cliente_nombre': e.destinatario_nombre,
        'numero_envio': e.codigo,
        'direccion': e.direccion_destino,
    },
)

engine = NotificationEngine()
res = engine.send_notification({'canal': 'sms', 'destinatario': u, 'plantilla': tpl, 'contexto': np.contenido_personalizado})

Notificacion.objects.create(
    titulo='Notificación inteligente',
    mensaje='Tu envío TEST-NOTIF-LOGIN-001 está en reparto hacia Av. Providencia 123.',
    tipo='info',
    canal='web',
    usuario=u,
)

print('ok', res)