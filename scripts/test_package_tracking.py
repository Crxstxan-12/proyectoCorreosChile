#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CorreosChile.settings')
django.setup()

from django.contrib.auth.models import User
from paquetes.models import TipoPaquete, Remitente, Destinatario, Paquete, PuntoEntrega, HistorialPaquete, RutaPaquete

def create_test_package():
    """Create a complete test package with tracking history"""
    print("Creating test package...")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@correoschile.cl', 'first_name': 'Test', 'last_name': 'User'}
    )
    
    # Get package types
    tipo_carta = TipoPaquete.objects.get(nombre='carta')
    
    # Get delivery points
    punto_santiago = PuntoEntrega.objects.get(codigo='SUC-SC-001')
    
    # Create sender
    remitente, created = Remitente.objects.get_or_create(
        tipo_documento='rut',
        numero_documento='12345678-9',
        defaults={
            'user': user,
            'nombre_completo': 'Juan Pérez González',
            'email': 'juan.perez@email.cl',
            'telefono': '+56912345678',
            'direccion': 'Av. Principal 1234, Depto 501',
            'comuna': 'Santiago',
            'region': 'Metropolitana',
            'codigo_postal': '7500000'
        }
    )
    
    # Create recipient
    destinatario, created = Destinatario.objects.get_or_create(
        tipo_documento='rut',
        numero_documento='98765432-1',
        defaults={
            'nombre_completo': 'María Rodríguez López',
            'email': 'maria.rodriguez@email.cl',
            'telefono': '+56987654321',
            'direccion': 'Calle Secundaria 567, Casa 2',
            'comuna': 'Providencia',
            'region': 'Metropolitana',
            'codigo_postal': '7500001',
            'instrucciones_entrega': 'Dejar en portería',
            'horario_preferido': 'Mañanas (9:00-13:00)',
            'es_direccion_comercial': False
        }
    )
    
    # Create package
    paquete = Paquete.objects.create(
        tipo_paquete=tipo_carta,
        remitente=remitente,
        destinatario=destinatario,
        peso_kg=0.3,
        largo_cm=21,
        ancho_cm=15,
        alto_cm=1,
        estado='registrado',
        prioridad='normal',
        valor_declarado=50000,
        monto_seguro=1000,
        requiere_seguro=True,
        forma_pago='efectivo',
        monto_total=2500,
        pagado=True,
        fecha_estimada_entrega='2025-11-25',
        descripcion_contenido='Documentos legales importantes',
        observaciones='Manejo con cuidado',
        instrucciones_especiales='Entregar solo a la destinataria',
        ubicacion_actual='Sucursal Santiago Centro',
        usuario_creacion=user
    )
    
    print(f"Package created: {paquete.codigo_seguimiento}")
    
    # Create tracking history
    historial_data = [
        {
            'estado_anterior': 'registrado',
            'estado_nuevo': 'en_almacen',
            'observacion': 'Paquete recibido en sucursal',
            'ubicacion': 'Sucursal Santiago Centro',
            'usuario': user
        },
        {
            'estado_anterior': 'en_almacen',
            'estado_nuevo': 'en_transito',
            'observacion': 'Paquete en camino a sucursal destino',
            'ubicacion': 'En tránsito hacia Providencia',
            'usuario': user
        },
        {
            'estado_anterior': 'en_transito',
            'estado_nuevo': 'en_reparto',
            'observacion': 'Paquete asignado a repartidor',
            'ubicacion': 'Sucursal Providencia',
            'usuario': user
        }
    ]
    
    for historial in historial_data:
        HistorialPaquete.objects.create(
            paquete=paquete,
            **historial
        )
    
    # Create route
    ruta = RutaPaquete.objects.create(
        paquete=paquete,
        origen='Sucursal Santiago Centro',
        destino='Sucursal Providencia',
        fecha_salida='2025-11-22 08:00:00',
        fecha_llegada='2025-11-22 10:30:00',
        orden_en_ruta=1,
        completado=True
    )
    
    print(f"Test package created successfully!")
    print(f"Tracking code: {paquete.codigo_seguimiento}")
    print(f"Current status: {paquete.get_estado_display()}")
    print(f"Route: {ruta.origen} → {ruta.destino}")
    print(f"Tracking history entries: {paquete.historial.count()}")
    
    return paquete

if __name__ == "__main__":
    paquete = create_test_package()
    print("\nTest completed successfully!")