from django.db import models
from envios.models import Envio
from notificaciones.models import Notificacion, PreferenciaNotificacion
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from notificaciones_mejoradas.models import PlantillaNotificacion, NotificacionProgramada, ConfiguracionNotificacion

class EventoSeguimiento(models.Model):
    ESTADOS = (
        ("pendiente", "pendiente"),
        ("en_transito", "en_transito"),
        ("en_planta", "en_planta"),
        ("en_reparto", "en_reparto"),
        ("entregado", "entregado"),
        ("incidencia", "incidencia"),
    )

    envio = models.ForeignKey(Envio, on_delete=models.CASCADE, related_name="eventos")
    estado = models.CharField(max_length=20, choices=ESTADOS)
    ubicacion = models.CharField(max_length=120)
    observacion = models.TextField(null=True, blank=True)
    registrado_en = models.DateTimeField(auto_now_add=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    foto_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.envio.codigo} - {self.estado} - {self.ubicacion}"

@receiver(post_save, sender=EventoSeguimiento)
def crear_notificacion_envio(sender, instance, created, **kwargs):
    if not created:
        return
    tipo = "info"
    if instance.estado == "incidencia":
        tipo = "alerta"
    usuario = getattr(instance.envio, 'usuario', None)
    if usuario:
        pref, _ = PreferenciaNotificacion.objects.get_or_create(usuario=usuario)
        canales = pref.canales_activos() or ["web"]
        for c in canales:
            Notificacion.objects.create(
                titulo=f"Estado actualizado: {instance.envio.codigo}",
                mensaje=(f"El envío cambió a '{instance.estado}' en {instance.ubicacion}. "
                         f"{('Detalle: ' + instance.observacion) if instance.observacion else ''}"),
                tipo=tipo,
                canal=c,
                usuario=usuario,
                envio=instance.envio,
            )
    else:
        Notificacion.objects.create(
            titulo=f"Estado actualizado: {instance.envio.codigo}",
            mensaje=(f"El envío cambió a '{instance.estado}' en {instance.ubicacion}. "
                     f"{('Detalle: ' + instance.observacion) if instance.observacion else ''}"),
            tipo=tipo,
            canal="web",
            envio=instance.envio,
        )

    # Notificaciones mejoradas por canal (email/SMS/WhatsApp)
    try:
        if usuario:
            config = ConfiguracionNotificacion.objects.filter(usuario=usuario, esta_activa=True).first()
            if config:
                # Determinar canal preferido
                if config.canal_whatsapp:
                    canal_pref = 'whatsapp'
                elif config.canal_sms:
                    canal_pref = 'sms'
                elif config.canal_email:
                    canal_pref = 'email'
                else:
                    canal_pref = 'email'

                # en_reparto → plantilla 'envio_en_reparto' con ETA
                if instance.estado == 'en_reparto':
                    try:
                        plantilla = PlantillaNotificacion.objects.get(tipo='envio_en_reparto', esta_activa=True)
                        eta = None
                        if getattr(instance.envio, 'fecha_estimada_entrega', None):
                            eta = instance.envio.fecha_estimada_entrega.strftime('%d/%m/%Y')
                        contexto = {
                            'cliente_nombre': instance.envio.destinatario_nombre,
                            'numero_envio': instance.envio.codigo,
                            'direccion': instance.envio.direccion_destino,
                            'hora_estimada': eta or 'Entre 9:00 y 18:00',
                            'estado_actual': 'En reparto',
                            'ubicacion_actual': instance.ubicacion,
                        }
                        NotificacionProgramada.objects.create(
                            envio=instance.envio,
                            plantilla=plantilla,
                            destinatario=usuario,
                            email_destino=usuario.email if canal_pref == 'email' else None,
                            telefono_destino=config.telefono_movil if canal_pref in ['sms','whatsapp'] else None,
                            canal_programado=canal_pref,
                            fecha_programada=timezone.now(),
                            contenido_personalizado=contexto,
                        )
                    except PlantillaNotificacion.DoesNotExist:
                        pass

                # incidencia → plantilla 'envio_demorado' con motivo
                if instance.estado == 'incidencia':
                    try:
                        plantilla = PlantillaNotificacion.objects.get(tipo='envio_demorado', esta_activa=True)
                        contexto = {
                            'cliente_nombre': instance.envio.destinatario_nombre,
                            'numero_envio': instance.envio.codigo,
                            'direccion': instance.envio.direccion_destino,
                            'razon_demora': instance.observacion or 'Motivo no especificado',
                            'nueva_fecha_estimada': None,
                            'estado_actual': 'Incidencia',
                            'ubicacion_actual': instance.ubicacion,
                        }
                        NotificacionProgramada.objects.create(
                            envio=instance.envio,
                            plantilla=plantilla,
                            destinatario=usuario,
                            email_destino=usuario.email if canal_pref == 'email' else None,
                            telefono_destino=config.telefono_movil if canal_pref in ['sms','whatsapp'] else None,
                            canal_programado=canal_pref,
                            fecha_programada=timezone.now(),
                            contenido_personalizado=contexto,
                        )
                    except PlantillaNotificacion.DoesNotExist:
                        pass
    except Exception:
        # Evitar que errores de notificaciones bloqueen el flujo de seguimiento
        pass
