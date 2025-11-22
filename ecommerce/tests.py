from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import PlataformaEcommerce, PedidoEcommerce, ProductoPedido, WebhookLog
from envios.models import Envio
import json
from datetime import datetime


class EcommerceIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.plataforma = PlataformaEcommerce.objects.create(
            nombre='Tienda Test',
            tipo='shopify',
            api_key='test_api_key',
            store_url='https://test.myshopify.com',
            usuario=self.user,
            esta_activa=True
        )

    def test_plataforma_creation(self):
        """Test crear plataforma e-commerce"""
        self.assertEqual(self.plataforma.nombre, 'Tienda Test')
        self.assertEqual(self.plataforma.tipo, 'shopify')
        self.assertTrue(self.plataforma.esta_activa)

    def test_pedido_creation(self):
        """Test crear pedido e-commerce"""
        pedido = PedidoEcommerce.objects.create(
            plataforma=self.plataforma,
            pedido_id_externo='12345',
            numero_orden='#1001',
            cliente_nombre='Juan Pérez',
            cliente_email='juan@example.com',
            direccion_entrega='Calle Test 123, Santiago',
            total=15000.00,
            estado='pendiente',
            fecha_pedido=datetime.now()
        )
        
        self.assertEqual(pedido.numero_orden, '#1001')
        self.assertEqual(pedido.cliente_nombre, 'Juan Pérez')
        self.assertEqual(pedido.estado, 'pendiente')

    def test_producto_pedido_creation(self):
        """Test crear producto de pedido"""
        pedido = PedidoEcommerce.objects.create(
            plataforma=self.plataforma,
            pedido_id_externo='12345',
            numero_orden='#1001',
            cliente_nombre='Juan Pérez',
            cliente_email='juan@example.com',
            direccion_entrega='Calle Test 123, Santiago',
            total=15000.00,
            estado='pendiente',
            fecha_pedido=datetime.now()
        )
        
        producto = ProductoPedido.objects.create(
            pedido=pedido,
            sku='TEST-001',
            nombre='Producto Test',
            cantidad=2,
            precio_unitario=5000.00,
            peso_kg=0.5
        )
        
        self.assertEqual(producto.nombre, 'Producto Test')
        self.assertEqual(producto.cantidad, 2)
        self.assertEqual(producto.subtotal, 10000.00)

    def test_webhook_log_creation(self):
        """Test crear log de webhook"""
        log = WebhookLog.objects.create(
            plataforma=self.plataforma,
            evento_tipo='orders/create',
            nivel='info',
            mensaje='Pedido recibido',
            ip_origen='192.168.1.1',
            procesado_exitoso=True
        )
        
        self.assertEqual(log.evento_tipo, 'orders/create')
        self.assertEqual(log.nivel, 'info')
        self.assertTrue(log.procesado_exitoso)

    def test_shopify_webhook_invalid_signature(self):
        """Test webhook con firma inválida"""
        webhook_data = {
            'id': '12345',
            'name': '#1001',
            'customer': {
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'email': 'juan@example.com'
            },
            'total_price': '15000.00',
            'currency': 'CLP',
            'created_at': '2024-01-01T12:00:00Z'
        }
        
        response = self.client.post(
            reverse('ecommerce:shopify_webhook', kwargs={'plataforma_id': self.plataforma.id}),
            data=json.dumps(webhook_data),
            content_type='application/json',
            HTTP_X_SHOPIFY_TOPIC='orders/create',
            HTTP_X_SHOPIFY_HMAC_SHA256='invalid_signature'
        )
        
        self.assertEqual(response.status_code, 401)

    def test_index_view_requires_login(self):
        """Test que la vista de index requiere login"""
        response = self.client.get(reverse('ecommerce:index'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_configurar_view_requires_permissions(self):
        """Test que la vista de configuración requiere permisos"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ecommerce:configurar'))
        self.assertEqual(response.status_code, 200)  # Should work for any authenticated user for GET