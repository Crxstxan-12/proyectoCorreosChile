# Script para configurar datos iniciales de prueba
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CorreosChile.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from ecommerce.models import PlataformaEcommerce, PedidoEcommerce, ProductoPedido
from envios.models import Envio
from seguimiento.models import EventoSeguimiento
from usuarios.models import Perfil
from transportista.models import Transportista

def setup_initial_data():
    print("Configurando datos iniciales...")
    
    # Configurar contraseña del admin
    try:
        admin = User.objects.get(username='admin')
        admin.set_password('admin123')
        admin.save()
        print("✅ Contraseña del admin configurada: admin123")
    except User.DoesNotExist:
        print("❌ Usuario admin no encontrado")
    
    # Crear usuario de prueba
    try:
        user_test, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        if created:
            user_test.set_password('test123')
            user_test.save()
            print("✅ Usuario de prueba creado: testuser / test123")
        else:
            print("✅ Usuario de prueba ya existe")
            
        # Crear perfil para el usuario
        perfil, _ = Perfil.objects.get_or_create(user=user_test)
        perfil.rol = 'administrador'
        perfil.save()
        print("✅ Perfil de administrador asignado")
        
    except Exception as e:
        print(f"❌ Error creando usuario de prueba: {e}")
    
    # Crear plataforma de prueba
    try:
        plataforma, created = PlataformaEcommerce.objects.get_or_create(
            nombre='Tienda Test Shopify',
            defaults={
                'tipo': 'shopify',
                'api_key': 'test_api_key_12345',
                'store_url': 'https://test-store.myshopify.com',
                'esta_activa': True,
                'usuario': user_test
            }
        )
        if created:
            print("✅ Plataforma de prueba creada")
        else:
            print("✅ Plataforma de prueba ya existe")
            
    except Exception as e:
        print(f"❌ Error creando plataforma: {e}")
    
    print("\n🎉 Configuración inicial completada!")
    print("\nCredenciales de acceso:")
    print("- Admin: admin / admin123")
    print("- Test: testuser / test123")
    print("\nURLs disponibles:")
    print("- Dashboard: http://127.0.0.1:8000/")
    print("- Admin Django: http://127.0.0.1:8000/admin/")
    print("- E-commerce: http://127.0.0.1:8000/ecommerce/")

    # Crear envío demo con código público y eventos
    try:
        envio, created = Envio.objects.get_or_create(
            codigo='CC251127241558',
            defaults={
                'estado': 'en_transito',
                'origen': 'Santiago',
                'destino': 'Providencia',
                'destinatario_nombre': 'Cliente Demo',
                'direccion_destino': 'Av. Demo 123, Providencia',
                'peso_kg': 2.5,
                'costo': 5990,
                'usuario': User.objects.filter(username='testuser').first()
            }
        )
        if created:
            print("✅ Envío demo creado: CC251127241558")
            EventoSeguimiento.objects.create(envio=envio, estado='pendiente', ubicacion='Recepción', observacion='Ingreso a sistema', lat=-33.45, lng=-70.6667)
            EventoSeguimiento.objects.create(envio=envio, estado='en_transito', ubicacion='Centro de distribución', observacion='Clasificación', lat=-33.47, lng=-70.65)
            EventoSeguimiento.objects.create(envio=envio, estado='en_reparto', ubicacion='Ruta de reparto', observacion='En camino', lat=-33.42, lng=-70.59)
        else:
            print("✅ Envío demo ya existe: CC251127241558")
    except Exception as e:
        print(f"❌ Error creando envío demo: {e}")

    # Crear transportistas demo
    try:
        Transportista.objects.get_or_create(nombre='Chilexpress', rut='76.123.456-7', defaults={'email':'ops@chilexpress.cl','tipo':'empresa','telefono':'+56223456700','direccion':'Santiago','activo':True})
        Transportista.objects.get_or_create(nombre='Starken', rut='76.765.432-1', defaults={'email':'ops@starken.cl','tipo':'empresa','telefono':'+56223456701','direccion':'Santiago','activo':True})
        Transportista.objects.get_or_create(nombre='Transportes Local', rut='12.345.678-9', defaults={'email':'local@transportes.cl','tipo':'independiente','telefono':'+56912345678','direccion':'Providencia','activo':True})
        print("✅ Transportistas demo listos")
    except Exception as e:
        print(f"❌ Error creando transportistas demo: {e}")

if __name__ == '__main__':
    setup_initial_data()
