# Script para crear datos de prueba en el sistema de paquetes

from django.core.management.base import BaseCommand
from paquetes.models import TipoPaquete, PuntoEntrega

class Command(BaseCommand):
    help = 'Crear datos de prueba para el sistema de paquetes'

    def handle(self, *args, **options):
        self.stdout.write('Creando tipos de paquetes...')
        
        # Crear tipos de paquetes
        tipos_data = [
            {
                'nombre': 'carta',
                'descripcion': 'Cartas y documentos pequeños',
                'dimensiones_max': 'A4 (21x29.7cm)',
                'peso_max_kg': 0.5,
                'tarifa_base': 1500,
                'tarifa_por_kg': 500,
                'tiempo_estimado_dias': 2,
                'requiere_firma': False,
                'seguro_incluido': False
            },
            {
                'nombre': 'sobre',
                'descripcion': 'Sobres y documentos medianos',
                'dimensiones_max': '35x25x3cm',
                'peso_max_kg': 1.0,
                'tarifa_base': 2500,
                'tarifa_por_kg': 800,
                'tiempo_estimado_dias': 2,
                'requiere_firma': False,
                'seguro_incluido': False
            },
            {
                'nombre': 'paquete_pequeno',
                'descripcion': 'Paquetes pequeños',
                'dimensiones_max': '30x20x15cm',
                'peso_max_kg': 2.0,
                'tarifa_base': 3500,
                'tarifa_por_kg': 1000,
                'tiempo_estimado_dias': 3,
                'requiere_firma': True,
                'seguro_incluido': True
            },
            {
                'nombre': 'paquete_mediano',
                'descripcion': 'Paquetes medianos',
                'dimensiones_max': '50x40x30cm',
                'peso_max_kg': 5.0,
                'tarifa_base': 5000,
                'tarifa_por_kg': 1200,
                'tiempo_estimado_dias': 3,
                'requiere_firma': True,
                'seguro_incluido': True
            },
            {
                'nombre': 'paquete_grande',
                'descripcion': 'Paquetes grandes',
                'dimensiones_max': '80x60x40cm',
                'peso_max_kg': 15.0,
                'tarifa_base': 8000,
                'tarifa_por_kg': 1500,
                'tiempo_estimado_dias': 4,
                'requiere_firma': True,
                'seguro_incluido': True
            },
            {
                'nombre': 'documento_urgente',
                'descripcion': 'Documentos urgentes',
                'dimensiones_max': 'A4 (21x29.7cm)',
                'peso_max_kg': 0.5,
                'tarifa_base': 5000,
                'tarifa_por_kg': 2000,
                'tiempo_estimado_dias': 1,
                'requiere_firma': True,
                'seguro_incluido': True
            }
        ]
        
        for tipo_data in tipos_data:
            TipoPaquete.objects.get_or_create(
                nombre=tipo_data['nombre'],
                defaults=tipo_data
            )
        
        self.stdout.write(self.style.SUCCESS('Tipos de paquetes creados exitosamente'))
        
        # Crear puntos de entrega
        self.stdout.write('Creando puntos de entrega...')
        
        puntos_data = [
            {
                'codigo': 'SUC-SC-001',
                'nombre': 'Sucursal Santiago Centro',
                'tipo': 'sucursal',
                'direccion': 'Av. Libertador Bernardo O\'Higgins 1234',
                'comuna': 'Santiago',
                'region': 'Metropolitana',
                'horario_apertura': '09:00',
                'horario_cierre': '18:00',
                'telefono': '+56223456789',
                'email': 'santiago@correoschile.cl',
                'latitud': -33.4489,
                'longitud': -70.6693,
                'activo': True
            },
            {
                'codigo': 'SUC-PR-002',
                'nombre': 'Sucursal Providencia',
                'tipo': 'sucursal',
                'direccion': 'Av. Providencia 2345',
                'comuna': 'Providencia',
                'region': 'Metropolitana',
                'horario_apertura': '09:00',
                'horario_cierre': '18:00',
                'telefono': '+56223456790',
                'email': 'providencia@correoschile.cl',
                'latitud': -33.4315,
                'longitud': -70.6111,
                'activo': True
            },
            {
                'codigo': 'CAS-LC-003',
                'nombre': 'Casilla Las Condes',
                'tipo': 'casilla',
                'direccion': 'Av. Apoquindo 3456',
                'comuna': 'Las Condes',
                'region': 'Metropolitana',
                'horario_apertura': '08:00',
                'horario_cierre': '20:00',
                'telefono': '+56223456791',
                'email': 'lascondes@correoschile.cl',
                'latitud': -33.3995,
                'longitud': -70.5475,
                'activo': True
            },
            {
                'codigo': 'LOC-NU-004',
                'nombre': 'Locker Ñuñoa',
                'tipo': 'locker',
                'direccion': 'Av. Irarrázaval 4567',
                'comuna': 'Ñuñoa',
                'region': 'Metropolitana',
                'horario_apertura': '00:00',
                'horario_cierre': '23:59',
                'telefono': '+56223456792',
                'email': 'nunoa@correoschile.cl',
                'latitud': -33.4578,
                'longitud': -70.5944,
                'activo': True
            }
        ]
        
        for punto_data in puntos_data:
            PuntoEntrega.objects.get_or_create(
                nombre=punto_data['nombre'],
                defaults=punto_data
            )
        
        self.stdout.write(self.style.SUCCESS('Puntos de entrega creados exitosamente'))
        self.stdout.write(self.style.SUCCESS('Datos de prueba creados exitosamente'))