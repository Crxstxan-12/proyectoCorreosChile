from django.utils import timezone
from .models import MantenimientoVehiculo


def flota_badges(request):
    try:
        hoy = timezone.now().date()
        programados = MantenimientoVehiculo.objects.filter(estado='programado').count()
        vencidos = MantenimientoVehiculo.objects.filter(estado='programado', fecha_programada__lt=hoy).count()
        return {
            'flota_mantenimientos_programados': programados,
            'flota_mantenimientos_vencidos': vencidos,
        }
    except Exception:
        return {
            'flota_mantenimientos_programados': 0,
            'flota_mantenimientos_vencidos': 0,
        }
