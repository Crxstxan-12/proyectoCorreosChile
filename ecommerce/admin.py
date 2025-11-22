from django.contrib import admin
from .models import PlataformaEcommerce, PedidoEcommerce, ProductoPedido, WebhookLog


@admin.register(PlataformaEcommerce)
class PlataformaEcommerceAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'store_url', 'esta_activa', 'usuario', 'creado_en']
    list_filter = ['tipo', 'esta_activa', 'creado_en']
    search_fields = ['nombre', 'store_url']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(usuario=request.user)


@admin.register(PedidoEcommerce)
class PedidoEcommerceAdmin(admin.ModelAdmin):
    list_display = ['numero_orden', 'plataforma', 'cliente_nombre', 'estado', 'total', 'creado_en']
    list_filter = ['estado', 'plataforma__tipo', 'creado_en']
    search_fields = ['numero_orden', 'cliente_nombre', 'cliente_email']
    readonly_fields = ['creado_en', 'actualizado_en']
    raw_id_fields = ['envio']


@admin.register(ProductoPedido)
class ProductoPedidoAdmin(admin.ModelAdmin):
    list_display = ['pedido', 'sku', 'nombre', 'cantidad', 'precio_unitario']
    search_fields = ['sku', 'nombre', 'pedido__numero_orden']
    list_filter = ['pedido__plataforma__tipo']


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['plataforma', 'evento_tipo', 'nivel', 'procesado_exitoso', 'creado_en']
    list_filter = ['nivel', 'procesado_exitoso', 'plataforma__tipo', 'creado_en']
    search_fields = ['evento_tipo', 'mensaje', 'evento_id']
    readonly_fields = ['creado_en']
    ordering = ['-creado_en']