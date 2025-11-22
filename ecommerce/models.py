from django.db import models
from django.contrib.auth.models import User
from envios.models import Envio


class PlataformaEcommerce(models.Model):
    PLATAFORMAS = (
        ('shopify', 'Shopify'),
        ('amazon', 'Amazon'),
        ('woocommerce', 'WooCommerce'),
        ('prestashop', 'PrestaShop'),
        ('custom', 'Personalizado'),
    )
    
    nombre = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=PLATAFORMAS)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)
    store_url = models.URLField()
    esta_activa = models.BooleanField(default=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"

    class Meta:
        verbose_name_plural = "Plataformas E-commerce"


class PedidoEcommerce(models.Model):
    ESTADOS_PEDIDO = (
        ('pendiente', 'Pendiente'),
        ('procesado', 'Procesado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
        ('error', 'Error'),
    )
    
    plataforma = models.ForeignKey(PlataformaEcommerce, on_delete=models.CASCADE, related_name='pedidos')
    pedido_id_externo = models.CharField(max_length=100)
    numero_orden = models.CharField(max_length=100)
    cliente_nombre = models.CharField(max_length=200)
    cliente_email = models.EmailField()
    cliente_telefono = models.CharField(max_length=50, blank=True, null=True)
    direccion_entrega = models.TextField()
    direccion_envio = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, default='CLP')
    estado = models.CharField(max_length=20, choices=ESTADOS_PEDIDO, default='pendiente')
    fecha_pedido = models.DateTimeField()
    fecha_envio = models.DateTimeField(blank=True, null=True)
    fecha_entrega = models.DateTimeField(blank=True, null=True)
    envio = models.OneToOneField(Envio, on_delete=models.SET_NULL, blank=True, null=True, related_name='pedido_ecommerce')
    datos_raw = models.JSONField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.numero_orden} - {self.cliente_nombre}"

    class Meta:
        unique_together = ('plataforma', 'pedido_id_externo')
        verbose_name_plural = "Pedidos E-commerce"


class ProductoPedido(models.Model):
    pedido = models.ForeignKey(PedidoEcommerce, on_delete=models.CASCADE, related_name='productos')
    sku = models.CharField(max_length=100)
    nombre = models.CharField(max_length=255)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    peso_kg = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    dimensiones = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return f"{self.cantidad}x {self.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class WebhookLog(models.Model):
    NIVELES_LOG = (
        ('info', 'Info'),
        ('advertencia', 'Advertencia'),
        ('error', 'Error'),
    )
    
    plataforma = models.ForeignKey(PlataformaEcommerce, on_delete=models.CASCADE, related_name='webhook_logs')
    evento_tipo = models.CharField(max_length=100)
    evento_id = models.CharField(max_length=100, blank=True, null=True)
    nivel = models.CharField(max_length=20, choices=NIVELES_LOG, default='info')
    mensaje = models.TextField()
    datos_recibidos = models.JSONField(blank=True, null=True)
    datos_procesados = models.JSONField(blank=True, null=True)
    ip_origen = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    procesado_exitoso = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.plataforma.nombre} - {self.evento_tipo} - {self.nivel}"

    class Meta:
        verbose_name_plural = "Logs de Webhooks"