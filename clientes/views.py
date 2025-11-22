from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Cliente, DireccionEntrega, ActividadCliente
from envios.models import Envio
from seguimiento.models import EventoSeguimiento
from notificaciones_mejoradas.models import NotificacionProgramada, HistorialNotificacion


@login_required
def dashboard_cliente(request):
    """Vista principal del dashboard del cliente"""
    try:
        cliente = request.user.cliente
    except Cliente.DoesNotExist:
        # Crear perfil de cliente si no existe
        cliente = Cliente.objects.create(user=request.user)
    
    # Registrar actividad
    ActividadCliente.objects.create(
        cliente=cliente,
        tipo='login',
        descripcion='Inicio de sesión en el dashboard',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Estadísticas del cliente
    total_envios = Envio.objects.filter(usuario=request.user).count()
    envios_activos = Envio.objects.filter(
        usuario=request.user,
        estado__in=['en_transito', 'en_reparto']
    ).count()
    envios_entregados = Envio.objects.filter(
        usuario=request.user,
        estado='entregado'
    ).count()
    
    # Envíos recientes
    envios_recientes = Envio.objects.filter(
        usuario=request.user
    ).order_by('-creado_en')[:5]
    
    # Notificaciones recientes
    notificaciones_recientes = HistorialNotificacion.objects.filter(
        cliente=cliente
    ).order_by('-fecha_envio')[:5]
    
    # Actividad reciente
    actividad_reciente = ActividadCliente.objects.filter(
        cliente=cliente
    ).order_by('-fecha')[:10]
    
    context = {
        'cliente': cliente,
        'total_envios': total_envios,
        'envios_activos': envios_activos,
        'envios_entregados': envios_entregados,
        'envios_recientes': envios_recientes,
        'notificaciones_recientes': notificaciones_recientes,
        'actividad_reciente': actividad_reciente,
    }
    
    return render(request, 'clientes/dashboard.html', context)


@login_required
def mis_envios(request):
    """Vista de listado de todos los envíos del cliente"""
    cliente = get_object_or_404(Cliente, user=request.user)
    
    # Filtros
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    busqueda = request.GET.get('busqueda', '')
    
    # Query base
    envios = Envio.objects.filter(usuario=request.user)
    
    # Aplicar filtros
    if estado:
        envios = envios.filter(estado=estado)
    
    if fecha_desde:
        try:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
            envios = envios.filter(creado_en__gte=fecha_desde)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            envios = envios.filter(creado_en__lte=fecha_hasta)
        except ValueError:
            pass
    
    if busqueda:
        envios = envios.filter(
            Q(codigo__icontains=busqueda) |
            Q(destinatario_nombre__icontains=busqueda) |
            Q(destino__icontains=busqueda)
        )
    
    # Ordenar por fecha más reciente
    envios = envios.order_by('-creado_en')
    
    # Registrar actividad
    ActividadCliente.objects.create(
        cliente=cliente,
        tipo='view_envio',
        descripcion=f'Consultó listado de envíos (filtros: estado={estado}, búsqueda={busqueda})',
        ip_address=get_client_ip(request)
    )
    
    context = {
        'envios': envios,
        'filtros': {
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'busqueda': busqueda,
        },
        'estados_posibles': Envio.ESTADOS,
    }
    
    return render(request, 'clientes/mis_envios.html', context)


@login_required
def detalle_envio(request, codigo):
    """Vista de detalle de un envío específico"""
    cliente = get_object_or_404(Cliente, user=request.user)
    envio = get_object_or_404(Envio, codigo=codigo, usuario=request.user)
    
    # Obtener eventos de seguimiento
    eventos = EventoSeguimiento.objects.filter(envio=envio).order_by('-fecha')
    
    # Obtener bultos asociados
    bultos = envio.bultos.all()
    
    # Registrar actividad
    ActividadCliente.objects.create(
        cliente=cliente,
        tipo='view_envio',
        descripcion=f'Visto detalle del envío {codigo}',
        ip_address=get_client_ip(request)
    )
    
    context = {
        'envio': envio,
        'eventos': eventos,
        'bultos': bultos,
        'google_maps_api_key': 'YOUR_GOOGLE_MAPS_API_KEY',  # Configurar en producción
    }
    
    return render(request, 'clientes/detalle_envio.html', context)


@login_required
def perfil_cliente(request):
    """Vista de perfil del cliente"""
    cliente = get_object_or_404(Cliente, user=request.user)
    direcciones = cliente.direcciones.filter(activa=True)
    
    if request.method == 'POST':
        # Actualizar información básica
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Actualizar información del cliente
        cliente.telefono = request.POST.get('telefono', '')
        cliente.direccion = request.POST.get('direccion', '')
        cliente.ciudad = request.POST.get('ciudad', '')
        cliente.codigo_postal = request.POST.get('codigo_postal', '')
        
        # Actualizar preferencias de notificación
        cliente.preferencias_email = 'preferencias_email' in request.POST
        cliente.preferencias_sms = 'preferencias_sms' in request.POST
        cliente.preferencias_whatsapp = 'preferencias_whatsapp' in request.POST
        cliente.preferencias_push = 'preferencias_push' in request.POST
        
        # Configuración de privacidad
        cliente.mostrar_telefono = 'mostrar_telefono' in request.POST
        cliente.mostrar_direccion = 'mostrar_direccion' in request.POST
        
        cliente.save()
        
        # Registrar actividad
        ActividadCliente.objects.create(
            cliente=cliente,
            tipo='update_perfil',
            descripcion='Actualización de información personal',
            ip_address=get_client_ip(request)
        )
        
        messages.success(request, 'Perfil actualizado correctamente')
        return redirect('perfil_cliente')
    
    context = {
        'cliente': cliente,
        'direcciones': direcciones,
    }
    
    return render(request, 'clientes/perfil.html', context)


@login_required
def preferencias_notificaciones(request):
    """Vista para gestionar preferencias de notificaciones"""
    cliente = get_object_or_404(Cliente, user=request.user)
    
    if request.method == 'POST':
        cliente.preferencias_email = 'preferencias_email' in request.POST
        cliente.preferencias_sms = 'preferencias_sms' in request.POST
        cliente.preferencias_whatsapp = 'preferencias_whatsapp' in request.POST
        cliente.preferencias_push = 'preferencias_push' in request.POST
        cliente.save()
        
        # Registrar actividad
        ActividadCliente.objects.create(
            cliente=cliente,
            tipo='cambio_preferencias',
            descripcion='Cambió preferencias de notificaciones',
            ip_address=get_client_ip(request)
        )
        
        messages.success(request, 'Preferencias de notificaciones actualizadas')
        return redirect('preferencias_notificaciones')
    
    context = {
        'cliente': cliente,
    }
    
    return render(request, 'clientes/preferencias_notificaciones.html', context)


@login_required
def notificaciones_cliente(request):
    """Vista de notificaciones del cliente"""
    cliente = get_object_or_404(Cliente, user=request.user)
    
    # Obtener notificaciones
    notificaciones = HistorialNotificacion.objects.filter(
        cliente=cliente
    ).order_by('-fecha_envio')
    
    # Marcar como leídas
    if request.method == 'POST':
        notificacion_id = request.POST.get('notificacion_id')
        if notificacion_id:
            try:
                notificacion = HistorialNotificacion.objects.get(
                    id=notificacion_id, 
                    cliente=cliente
                )
                notificacion.leido = True
                notificacion.fecha_lectura = timezone.now()
                notificacion.save()
                return JsonResponse({'success': True})
            except HistorialNotificacion.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Notificación no encontrada'})
    
    context = {
        'notificaciones': notificaciones,
        'no_leidas': notificaciones.filter(leido=False).count()
    }
    
    return render(request, 'clientes/notificaciones.html', context)


@login_required
def agregar_direccion(request):
    """Vista para agregar nueva dirección de entrega"""
    cliente = get_object_or_404(Cliente, user=request.user)
    
    if request.method == 'POST':
        direccion = DireccionEntrega.objects.create(
            cliente=cliente,
            nombre=request.POST.get('nombre', ''),
            direccion=request.POST.get('direccion', ''),
            ciudad=request.POST.get('ciudad', ''),
            codigo_postal=request.POST.get('codigo_postal', ''),
            telefono_contacto=request.POST.get('telefono_contacto', ''),
            instrucciones=request.POST.get('instrucciones', ''),
            es_principal=request.POST.get('es_principal') == 'on'
        )
        
        # Registrar actividad
        ActividadCliente.objects.create(
            cliente=cliente,
            tipo='cambio_direccion',
            descripcion=f'Agregó nueva dirección: {direccion.nombre}',
            ip_address=get_client_ip(request)
        )
        
        messages.success(request, 'Dirección agregada correctamente')
        return redirect('perfil_cliente')
    
    return render(request, 'clientes/agregar_direccion.html')


@login_required
def descargar_reporte(request):
    """Vista para descargar reporte de envíos"""
    cliente = get_object_or_404(Cliente, user=request.user)
    
    # Obtener envíos del último mes
    fecha_hace_un_mes = timezone.now() - timedelta(days=30)
    envios = Envio.objects.filter(
        usuario=request.user,
        creado_en__gte=fecha_hace_un_mes
    ).order_by('-creado_en')
    
    # Registrar actividad
    ActividadCliente.objects.create(
        cliente=cliente,
        tipo='descarga_reporte',
        descripcion='Descargó reporte de envíos',
        ip_address=get_client_ip(request)
    )
    
    # Crear reporte CSV
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_envios_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Código', 'Destinatario', 'Destino', 'Estado', 'Fecha de Creación', 'Peso (kg)', 'Costo'])
    
    for envio in envios:
        writer.writerow([
            envio.codigo,
            envio.destinatario_nombre,
            envio.destino,
            envio.get_estado_display(),
            envio.creado_en.strftime('%d/%m/%Y %H:%M'),
            envio.peso_kg or 'N/A',
            envio.costo or 'N/A'
        ])
    
    return response


def get_client_ip(request):
    """Obtener IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
