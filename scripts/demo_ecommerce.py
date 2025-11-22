# Script de demo para probar la integración e-commerce
import os
import django
import json
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CorreosChile.settings')
django.setup()

from django.contrib.auth.models import User
from ecommerce.models import PlataformaEcommerce, PedidoEcommerce, ProductoPedido, WebhookLog
from django.test import Client

def demo_shopify_webhook():
    print("🚀 Demo: Probando integración Shopify")
    
    # Obtener plataforma de prueba
    try:
        plataforma = PlataformaEcommerce.objects.get(nombre='Tienda Test Shopify')
        print(f"✅ Plataforma encontrada: {plataforma.nombre}")
    except PlataformaEcommerce.DoesNotExist:
        print("❌ Plataforma no encontrada")
        return
    
    # Datos de ejemplo de Shopify
    shopify_order_data = {
        "id": "1234567890",
        "name": "#DEMO1001",
        "customer": {
            "first_name": "María",
            "last_name": "González",
            "email": "maria@example.com"
        },
        "phone": "+56912345678",
        "total_price": "25000.00",
        "currency": "CLP",
        "created_at": "2024-11-21T10:30:00Z",
        "shipping_address": {
            "address1": "Av. Principal 123",
            "address2": "",
            "city": "Santiago",
            "province": "RM",
            "zip": "7500000",
            "country": "Chile"
        },
        "billing_address": {
            "address1": "Av. Principal 123",
            "city": "Santiago",
            "province": "RM",
            "zip": "7500000",
            "country": "Chile"
        },
        "line_items": [
            {
                "id": 1,
                "sku": "PROD-001",
                "name": "Producto de Prueba 1",
                "quantity": 2,
                "price": "8000.00",
                "grams": 500
            },
            {
                "id": 2,
                "sku": "PROD-002", 
                "name": "Producto de Prueba 2",
                "quantity": 1,
                "price": "9000.00",
                "grams": 750
            }
        ]
    }
    
    # Simular webhook de Shopify
    client = Client()
    
    # Calcular HMAC (simulado - en producción debería usar el secreto real)
    import hmac
    import hashlib
    import base64
    
    webhook_secret = plataforma.webhook_secret or 'test_secret'
    body = json.dumps(shopify_order_data).encode('utf-8')
    hash_hmac = hmac.new(webhook_secret.encode('utf-8'), body, hashlib.sha256).digest()
    computed_hmac = base64.b64encode(hash_hmac).decode('utf-8')
    
    print("📤 Enviando webhook de prueba...")
    
    response = client.post(
        f'/ecommerce/webhook/shopify/{plataforma.id}/',
        data=json.dumps(shopify_order_data),
        content_type='application/json',
        HTTP_X_SHOPIFY_TOPIC='orders/create',
        HTTP_X_SHOPIFY_HMAC_SHA256=computed_hmac,
        HTTP_X_SHOPIFY_SHOP_DOMAIN='test-store.myshopify.com'
    )
    
    print(f"📊 Código de respuesta: {response.status_code}")
    print(f"📄 Respuesta: {response.json()}")
    
    if response.status_code == 200:
        print("✅ Webhook procesado exitosamente")
        
        # Verificar que se creó el pedido
        try:
            pedido = PedidoEcommerce.objects.get(
                plataforma=plataforma,
                pedido_id_externo='1234567890'
            )
            print(f"✅ Pedido creado: {pedido.numero_orden}")
            print(f"✅ Cliente: {pedido.cliente_nombre}")
            print(f"✅ Total: ${pedido.total}")
            print(f"✅ Productos: {pedido.productos.count()}")
            
            if pedido.envio:
                print(f"✅ Envío creado: {pedido.envio.codigo}")
                print(f"✅ Bultos: {pedido.envio.bultos.count()}")
            
            # Verificar logs
            logs = WebhookLog.objects.filter(plataforma=plataforma)
            print(f"✅ Logs creados: {logs.count()}")
            
        except PedidoEcommerce.DoesNotExist:
            print("❌ Pedido no encontrado")
    else:
        print("❌ Error procesando webhook")
        print(f"Error: {response.content}")

def demo_configuracion():
    print("\n🔧 Demo: Configuración de plataforma")
    
    try:
        plataforma = PlataformaEcommerce.objects.get(nombre='Tienda Test Shopify')
        print(f"📋 Plataforma: {plataforma.nombre}")
        print(f"📋 Tipo: {plataforma.get_tipo_display()}")
        print(f"📋 URL: {plataforma.store_url}")
        print(f"📋 Estado: {'Activa' if plataforma.esta_activa else 'Inactiva'}")
        
        # Mostrar URL de webhook
        webhook_url = f"http://127.0.0.1:8000/ecommerce/webhook/shopify/{plataforma.id}/"
        print(f"📋 Webhook URL: {webhook_url}")
        
    except PlataformaEcommerce.DoesNotExist:
        print("❌ Plataforma no encontrada")

if __name__ == '__main__':
    print("🎯 Demo de Integración E-commerce - CorreosChile")
    print("=" * 50)
    
    demo_configuracion()
    print("\n" + "=" * 50)
    demo_shopify_webhook()
    
    print("\n🎉 Demo completada!")
    print("\nPara probar manualmente:")
    print("1. Inicia el servidor: python manage.py runserver")
    print("2. Accede a: http://127.0.0.1:8000/ecommerce/")
    print("3. Usuario: testuser / Contraseña: test123")