from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from usuarios.models import Perfil
from transportista.models import Transportista
from envios.models import Envio, Bulto
from seguimiento.models import EventoSeguimiento

class Command(BaseCommand):
    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(username='admin', defaults={'email':'admin@example.com'})
        admin.set_password('admin123')
        admin.save()
        user_test, _ = User.objects.get_or_create(username='testuser', defaults={'email':'test@example.com', 'first_name':'Test', 'last_name':'User'})
        user_test.set_password('test123')
        user_test.save()
        perfil, _ = Perfil.objects.get_or_create(user=user_test)
        perfil.rol = 'administrador'
        perfil.save()
        Transportista.objects.get_or_create(nombre='Chilexpress', rut='76.123.456-7', defaults={'email':'ops@chilexpress.cl','tipo':'empresa','telefono':'+56223456700','direccion':'Santiago','activo':True})
        Transportista.objects.get_or_create(nombre='Starken', rut='76.765.432-1', defaults={'email':'ops@starken.cl','tipo':'empresa','telefono':'+56223456701','direccion':'Santiago','activo':True})
        Transportista.objects.get_or_create(nombre='Transportes Local', rut='12.345.678-9', defaults={'email':'local@transportes.cl','tipo':'independiente','telefono':'+56912345678','direccion':'Providencia','activo':True})
        envio, _ = Envio.objects.get_or_create(codigo='TEST-NOTIF-LOGIN-001', defaults={'estado':'en_transito','origen':'Santiago','destino':'Providencia','destinatario_nombre':'Cliente Demo','direccion_destino':'Av. Demo 123, Providencia','peso_kg':2.5,'costo':5990,'usuario':user_test})
        for i in range(1,4):
            Bulto.objects.get_or_create(envio=envio, codigo_barras=f"{envio.codigo}-SKU1-{i}")
        if not EventoSeguimiento.objects.filter(envio=envio).exists():
            EventoSeguimiento.objects.create(envio=envio, estado='pendiente', ubicacion='Recepción', observacion='Ingreso a sistema', lat=-33.45, lng=-70.6667)
            EventoSeguimiento.objects.create(envio=envio, estado='en_transito', ubicacion='Centro de distribución', observacion='Clasificación', lat=-33.47, lng=-70.65)
            EventoSeguimiento.objects.create(envio=envio, estado='en_reparto', ubicacion='Ruta de reparto', observacion='En camino', lat=-33.42, lng=-70.59)
        self.stdout.write(self.style.SUCCESS('Seed de envíos demo completado'))
