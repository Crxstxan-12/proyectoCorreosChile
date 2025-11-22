from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Count, Q
from .models import Conductor, RutaConductor, EnvioRuta, IncidenciaConductor, MetricasConductor
from envios.models import Envio
import json


@login_required
def dashboard_conductor(request):
    """Dashboard principal para conductores (versión web)"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        messages.error(request, 'No tienes perfil de conductor')
        return redirect('usuarios:index')
    
    # Obtener métricas del día actual
    hoy = timezone.now().date()
    
    # Ruta actual en progreso
    ruta_actual = RutaConductor.objects.filter(
        conductor=conductor,
        estado='en_progreso'
    ).first()
    
    # Estadísticas del día
    metricas_hoy, created = MetricasConductor.objects.get_or_create(
        conductor=conductor,
        fecha=hoy,
        defaults={
            'total_envios_entregados': 0,
            'total_envios_fallidos': 0,
            'total_kilometros_recorridos': 0,
            'tiempo_total_trabajado_minutos': 0,
        }
    )
    
    # Envíos pendientes de hoy
    if ruta_actual:
        envios_pendientes = EnvioRuta.objects.filter(
            ruta=ruta_actual,
            estado__in=['pendiente', 'en_camino']
        ).order_by('orden_entrega')[:5]
    else:
        envios_pendientes = []
    
    # Incidencias recientes
    incidencias_recientes = IncidenciaConductor.objects.filter(
        conductor=conductor,
        fecha_reporte__date=hoy
    ).order_by('-fecha_reporte')[:3]
    
    # Historial de rutas recientes
    rutas_recientes = RutaConductor.objects.filter(
        conductor=conductor
    ).exclude(estado='en_progreso').order_by('-fecha')[:5]
    
    context = {
        'conductor': conductor,
        'ruta_actual': ruta_actual,
        'metricas_hoy': metricas_hoy,
        'envios_pendientes': envios_pendientes,
        'incidencias_recientes': incidencias_recientes,
        'rutas_recientes': rutas_recientes,
        'hoy': hoy,
    }
    
    return render(request, 'conductores/dashboard.html', context)


@login_required
def mis_rutas(request):
    """Listado de rutas del conductor"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        messages.error(request, 'No tienes perfil de conductor')
        return redirect('usuarios:index')
    
    rutas = RutaConductor.objects.filter(
        conductor=conductor
    ).order_by('-fecha')
    
    # Filtros
    estado = request.GET.get('estado')
    fecha = request.GET.get('fecha')
    
    if estado:
        rutas = rutas.filter(estado=estado)
    
    if fecha:
        rutas = rutas.filter(fecha=fecha)
    
    context = {
        'conductor': conductor,
        'rutas': rutas,
        'estados': RutaConductor.ESTADOS_RUTA,
    }
    
    return render(request, 'conductores/mis_rutas.html', context)


@login_required
def detalle_ruta(request, ruta_id):
    """Detalle de una ruta específica"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        messages.error(request, 'No tienes perfil de conductor')
        return redirect('usuarios:index')
    
    ruta = get_object_or_404(RutaConductor, id=ruta_id, conductor=conductor)
    envios_ruta = EnvioRuta.objects.filter(ruta=ruta).order_by('orden_entrega')
    
    # Estadísticas de la ruta
    envios_pendientes = envios_ruta.filter(estado='pendiente').count()
    envios_entregados = envios_ruta.filter(estado='entregado').count()
    envios_fallidos = envios_ruta.filter(estado='fallido').count()
    
    context = {
        'conductor': conductor,
        'ruta': ruta,
        'envios_ruta': envios_ruta,
        'envios_pendientes': envios_pendientes,
        'envios_entregados': envios_entregados,
        'envios_fallidos': envios_fallidos,
        'progreso': ruta.progreso,
    }
    
    return render(request, 'conductores/detalle_ruta.html', context)


@login_required
def mis_incidencias(request):
    """Listado de incidencias del conductor"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        messages.error(request, 'No tienes perfil de conductor')
        return redirect('usuarios:index')
    
    incidencias = IncidenciaConductor.objects.filter(
        conductor=conductor
    ).order_by('-fecha_reporte')
    
    # Filtros
    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')
    
    if tipo:
        incidencias = incidencias.filter(tipo=tipo)
    
    if estado:
        incidencias = incidencias.filter(estado=estado)
    
    context = {
        'conductor': conductor,
        'incidencias': incidencias,
        'tipos': IncidenciaConductor.TIPOS_INCIDENCIA,
        'estados': IncidenciaConductor.ESTADOS_INCIDENCIA,
    }
    
    return render(request, 'conductores/mis_incidencias.html', context)


@login_required
def crear_incidencia(request):
    """Crear nueva incidencia"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        messages.error(request, 'No tienes perfil de conductor')
        return redirect('usuarios:index')
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        tipo = request.POST.get('tipo')
        latitud = request.POST.get('latitud')
        longitud = request.POST.get('longitud')
        envio_id = request.POST.get('envio_afectado')
        
        if titulo and descripcion and tipo:
            incidencia = IncidenciaConductor.objects.create(
                conductor=conductor,
                titulo=titulo,
                descripcion=descripcion,
                tipo=tipo,
                latitud=latitud if latitud else None,
                longitud=longitud if longitud else None,
                envio_afectado_id=envio_id if envio_id else None
            )
            
            # Manejo de fotos
            for i in range(1, 4):
                foto = request.FILES.get(f'foto{i}')
                if foto:
                    setattr(incidencia, f'foto{i}', foto)
            
            incidencia.save()
            
            messages.success(request, 'Incidencia creada correctamente')
            return redirect('conductores:mis_incidencias')
        else:
            messages.error(request, 'Por favor completa todos los campos obligatorios')
    
    # Obtener envíos del conductor para asociar
    envios_conductor = Envio.objects.filter(
        rutas__ruta__conductor=conductor,
        rutas__estado__in=['pendiente', 'en_camino', 'entregado', 'fallido']
    ).distinct()[:10]
    
    context = {
        'conductor': conductor,
        'tipos': IncidenciaConductor.TIPOS_INCIDENCIA,
        'envios_conductor': envios_conductor,
    }
    
    return render(request, 'conductores/crear_incidencia.html', context)


@login_required
def mi_perfil_conductor(request):
    """Perfil del conductor"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        messages.error(request, 'No tienes perfil de conductor')
        return redirect('usuarios:index')
    
    if request.method == 'POST':
        # Actualizar información básica
        telefono = request.POST.get('telefono')
        vehiculo_asignado = request.POST.get('vehiculo_asignado')
        placa_vehiculo = request.POST.get('placa_vehiculo')
        hora_inicio_jornada = request.POST.get('hora_inicio_jornada')
        hora_fin_jornada = request.POST.get('hora_fin_jornada')
        
        conductor.telefono = telefono
        conductor.vehiculo_asignado = vehiculo_asignado
        conductor.placa_vehiculo = placa_vehiculo
        conductor.hora_inicio_jornada = hora_inicio_jornada
        conductor.hora_fin_jornada = hora_fin_jornada
        conductor.save()
        
        messages.success(request, 'Perfil actualizado correctamente')
        return redirect('conductores:mi_perfil')
    
    # Métricas generales
    total_envios = EnvioRuta.objects.filter(
        ruta__conductor=conductor,
        estado='entregado'
    ).count()
    
    total_km = conductor.total_kilometros_recorridos
    
    # Últimas métricas
    ultimas_metricas = MetricasConductor.objects.filter(
        conductor=conductor
    ).order_by('-fecha')[:7]
    
    context = {
        'conductor': conductor,
        'total_envios': total_envios,
        'total_km': total_km,
        'ultimas_metricas': ultimas_metricas,
    }
    
    return render(request, 'conductores/mi_perfil.html', context)


@login_required
@require_POST
def actualizar_estado(request):
    """Actualizar estado del conductor (AJAX)"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        return JsonResponse({'error': 'No eres conductor'}, status=403)
    
    nuevo_estado = request.POST.get('estado')
    
    if nuevo_estado in [choice[0] for choice in Conductor.ESTADOS_CONDUCTOR]:
        conductor.cambiar_estado(nuevo_estado)
        return JsonResponse({
            'status': 'success',
            'message': f'Estado actualizado a {nuevo_estado}',
            'estado': nuevo_estado
        })
    else:
        return JsonResponse({'error': 'Estado inválido'}, status=400)


@login_required
@require_POST
def actualizar_ubicacion(request):
    """Actualizar ubicación del conductor (AJAX)"""
    try:
        conductor = request.user.conductor
    except Conductor.DoesNotExist:
        return JsonResponse({'error': 'No eres conductor'}, status=403)
    
    try:
        data = json.loads(request.body)
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if latitud and longitud:
            conductor.actualizar_ubicacion(latitud, longitud)
            return JsonResponse({
                'status': 'success',
                'message': 'Ubicación actualizada',
                'latitud': latitud,
                'longitud': longitud
            })
        else:
            return JsonResponse({'error': 'Latitud y longitud requeridas'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
