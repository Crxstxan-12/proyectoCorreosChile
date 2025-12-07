from django.db.models.signals import post_save
from django.dispatch import receiver
from seguimiento.models import EventoSeguimiento
from .models import PedidoEcommerce
from .services import sync_estado_a_plataforma

@receiver(post_save, sender=EventoSeguimiento)
def sync_estado_ecommerce(sender, instance, created, **kwargs):
    if not created:
        return
    envio = instance.envio
    pedido = getattr(envio, 'pedido_ecommerce', None)
    if not pedido:
        return
    sync_estado_a_plataforma(pedido, instance.estado, tracking_codigo=getattr(envio, 'codigo', None))
