from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg, F
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta

from .models import TipoVehiculo, Vehiculo, MantenimientoVehiculo, RepuestoVehiculo, UsoRepuestoMantenimiento
from conductores.models import Conductor


@login_required
def dashboard_flota(request):
    """Dashboard principal de gestión de flota"""
    # Estadísticas generales
    total_vehiculos = Vehiculo.objects.count()
    vehiculos_disponibles = Vehiculo.objects.filter(estado='disponible').count()
    vehiculos_en_uso = Vehiculo.objects.filter(estado='en_uso').count()
    vehiculos_operativos = vehiculos_disponibles + vehiculos_en_uso
    vehiculos_mantenimiento = Vehiculo.objects.filter(estado='mantenimiento').count()
    vehiculos_fuera_servicio = Vehiculo.objects.filter(estado='fuera_servicio').count()

    # Mantenimientos
    hoy = timezone.now().date()
    fecha_limite = hoy + timedelta(days=7)

    mantenimientos_pendientes = MantenimientoVehiculo.objects.filter(estado='programado').count()
    mantenimientos_proximos_7_dias = MantenimientoVehiculo.objects.filter(
        estado='programado',
        fecha_programada__lte=fecha_limite
    ).count()

    # Costos del mes actual
    primer_dia_mes = hoy.replace(day=1)
    costo_mantenimiento_mes = MantenimientoVehiculo.objects.filter(
        estado='completado',
        fecha_fin__date__gte=primer_dia_mes
    ).aggregate(total=Sum('costo_total'))['total'] or 0

    # Consumo promedio
    promedio_consumo = Vehiculo.objects.aggregate(promedio=Avg('consumo_promedio_km'))['promedio'] or 0

    # Vehículos que requieren mantenimiento (por km o fecha)
    vehiculos_requieren_mantenimiento = Vehiculo.objects.filter(es_activo=True).filter(
        Q(proximo_mantenimiento_km__isnull=False, proximo_mantenimiento_km__lte=F('kilometraje_actual')) |
        Q(proximo_mantenimiento_fecha__isnull=False, proximo_mantenimiento_fecha__lte=hoy)
    ).select_related('tipo_vehiculo', 'conductor_asignado__usuario')[:10]

    # Mantenimientos próximos
    mantenimientos_proximos = MantenimientoVehiculo.objects.filter(
        estado='programado',
        fecha_programada__lte=fecha_limite
    ).select_related('vehiculo__tipo_vehiculo').order_by('fecha_programada')[:10]

    context = {
        'total_vehiculos': total_vehiculos,
        'vehiculos_operativos': vehiculos_operativos,
        'vehiculos_mantenimiento': vehiculos_mantenimiento,
        'vehiculos_fuera_servicio': vehiculos_fuera_servicio,
        'mantenimientos_pendientes': mantenimientos_pendientes,
        'mantenimientos_proximos_7_dias': mantenimientos_proximos_7_dias,
        'costo_mantenimiento_mes': costo_mantenimiento_mes,
        'promedio_consumo_combustible': round(promedio_consumo or 0, 2),
        'vehiculos_requieren_mantenimiento': vehiculos_requieren_mantenimiento,
        'mantenimientos_proximos': mantenimientos_proximos,
        'today': hoy,
    }

    return render(request, 'flota/dashboard_flota.html', context)


@login_required
def lista_vehiculos(request):
    """Lista de vehículos con filtros"""
    
    # Obtener vehículos con relaciones
    vehiculos = Vehiculo.objects.select_related('tipo_vehiculo', 'conductor_asignado__usuario').all()
    
    # Filtros
    estado = request.GET.get('estado')
    if estado:
        vehiculos = vehiculos.filter(estado=estado)
    
    tipo = request.GET.get('tipo')
    if tipo:
        vehiculos = vehiculos.filter(tipo_vehiculo_id=tipo)
    
    conductor = request.GET.get('conductor')
    if conductor:
        vehiculos = vehiculos.filter(conductor_asignado_id=conductor)
    
    # Filtro de mantenimiento: mostrar solo los que requieren mantenimiento
    mantenimiento = request.GET.get('mantenimiento')
    if mantenimiento == 'requiere':
        vehiculos = vehiculos.filter(
            Q(proximo_mantenimiento_km__isnull=False, proximo_mantenimiento_km__lte=F('kilometraje_actual')) |
            Q(proximo_mantenimiento_fecha__isnull=False, proximo_mantenimiento_fecha__lte=timezone.now().date())
        )
    
    # Búsqueda
    search = request.GET.get('search')
    if search:
        vehiculos = vehiculos.filter(
            Q(numero_placa__icontains=search) |
            Q(marca__icontains=search) |
            Q(modelo__icontains=search) |
            Q(numero_chasis__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(vehiculos, 20)
    page = request.GET.get('page')
    vehiculos_page = paginator.get_page(page)
    
    # Opciones para filtros
    tipos_vehiculo = TipoVehiculo.objects.filter(es_activo=True)
    conductores = Conductor.objects.select_related('usuario').all()
    
    context = {
        'vehiculos': vehiculos_page,
        'tipos_vehiculo': tipos_vehiculo,
        'conductores': conductores,
        'estados_vehiculo': Vehiculo.ESTADO_VEHICULO,
        'filtros': {
            'estado': estado,
            'tipo': tipo,
            'conductor': conductor,
            'mantenimiento': mantenimiento,
            'search': search,
        }
    }
    
    return render(request, 'flota/lista_vehiculos.html', context)


@login_required
def detalle_vehiculo(request, vehiculo_id):
    """Detalle de un vehículo específico"""
    
    vehiculo = get_object_or_404(
        Vehiculo.objects.select_related('tipo_vehiculo', 'conductor_asignado__usuario'),
        id=vehiculo_id
    )
    
    # Mantenimientos del vehículo
    mantenimientos = vehiculo.mantenimientos.select_related('vehiculo__tipo_vehiculo').order_by('-fecha_realizacion')[:10]
    
    # Mantenimientos pendientes
    mantenimientos_pendientes = vehiculo.mantenimientos.filter(
        estado='pendiente'
    ).order_by('fecha_programada')
    
    # Calcular estadísticas
    total_mantenimientos = vehiculo.mantenimientos.count()
    mantenimientos_completados = vehiculo.mantenimientos.filter(estado='completado').count()
    costo_total_mantenimientos = vehiculo.mantenimientos.filter(
        estado='completado'
    ).aggregate(total=Sum('costo_mano_obra'))['total'] or 0
    
    # Calcular días desde último mantenimiento
    dias_ultimo_mantenimiento = None
    if vehiculo.ultimo_mantenimiento:
        dias_ultimo_mantenimiento = (timezone.now().date() - vehiculo.ultimo_mantenimiento).days
    
    context = {
        'vehiculo': vehiculo,
        'mantenimientos': mantenimientos,
        'mantenimientos_pendientes': mantenimientos_pendientes,
        'total_mantenimientos': total_mantenimientos,
        'mantenimientos_completados': mantenimientos_completados,
        'costo_total_mantenimientos': costo_total_mantenimientos,
        'dias_ultimo_mantenimiento': dias_ultimo_mantenimiento,
    }
    
    return render(request, 'flota/detalle_vehiculo.html', context)


@login_required
def asignar_conductor(request, vehiculo_id):
    """Asignar conductor a vehículo"""
    
    vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id)
    
    if request.method == 'POST':
        conductor_id = request.POST.get('conductor_id')
        
        if conductor_id:
            try:
                conductor = Conductor.objects.get(id=conductor_id)
                
                # Verificar si el conductor ya tiene un vehículo asignado
                if Vehiculo.objects.filter(conductor_asignado=conductor).exclude(id=vehiculo.id).exists():
                    messages.error(request, 'El conductor ya tiene un vehículo asignado')
                else:
                    vehiculo.conductor_asignado = conductor
                    vehiculo.save()
                    messages.success(request, f'Conductor {conductor.usuario.get_full_name()} asignado exitosamente')
                    return redirect('flota:detalle_vehiculo', vehiculo_id=vehiculo.id)
                    
            except Conductor.DoesNotExist:
                messages.error(request, 'Conductor no encontrado')
        else:
            messages.error(request, 'Debe seleccionar un conductor')
    
    # Conductores disponibles (sin vehículo asignado)
    conductores_disponibles = Conductor.objects.filter(
        Q(vehiculo_asignado__isnull=True) | Q(vehiculo_asignado=vehiculo)
    ).select_related('usuario')
    
    context = {
        'vehiculo': vehiculo,
        'conductores_disponibles': conductores_disponibles,
    }
    
    return render(request, 'flota/asignar_conductor.html', context)


@login_required
def desasignar_conductor(request, vehiculo_id):
    """Desasignar conductor de vehículo"""
    
    vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id)
    
    if request.method == 'POST':
        conductor_nombre = vehiculo.conductor_asignado.usuario.get_full_name() if vehiculo.conductor_asignado else None
        vehiculo.conductor_asignado = None
        vehiculo.save()
        
        if conductor_nombre:
            messages.success(request, f'Conductor {conductor_nombre} desasignado exitosamente')
        else:
            messages.success(request, 'Vehículo desasignado exitosamente')
    
    return redirect('flota:detalle_vehiculo', vehiculo_id=vehiculo.id)


@login_required
def programar_mantenimiento(request, vehiculo_id):
    """Programar mantenimiento para vehículo"""
    
    vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id)
    
    if request.method == 'POST':
        tipo_mantenimiento = request.POST.get('tipo_mantenimiento')
        descripcion = request.POST.get('descripcion')
        fecha_programada = request.POST.get('fecha_programada')
        titulo = request.POST.get('titulo') or f"Mantenimiento {tipo_mantenimiento} - {vehiculo.numero_placa}"
        
        if tipo_mantenimiento and fecha_programada:
            try:
                mantenimiento = MantenimientoVehiculo.objects.create(
                    vehiculo=vehiculo,
                    tipo_mantenimiento=tipo_mantenimiento,
                    estado='programado',
                    titulo=titulo,
                    descripcion=descripcion or '',
                    kilometraje_actual=vehiculo.kilometraje_actual,
                    fecha_programada=datetime.strptime(fecha_programada, '%Y-%m-%d').date(),
                    costo_mano_obra=0,
                )
                
                messages.success(request, 'Mantenimiento programado exitosamente')
                return redirect('flota:detalle_vehiculo', vehiculo_id=vehiculo.id)
                
            except Exception as e:
                messages.error(request, f'Error al programar mantenimiento: {str(e)}')
        else:
            messages.error(request, 'Todos los campos son requeridos')
    
    context = {
        'vehiculo': vehiculo,
        'tipos_mantenimiento': MantenimientoVehiculo.TIPO_MANTENIMIENTO,
    }
    
    return render(request, 'flota/programar_mantenimiento.html', context)


@login_required
def lista_mantenimientos(request):
    """Lista de mantenimientos con filtros"""
    
    # Obtener mantenimientos con relaciones
    mantenimientos = MantenimientoVehiculo.objects.select_related('vehiculo__tipo_vehiculo').all()
    
    # Filtros
    vehiculo_id = request.GET.get('vehiculo')
    if vehiculo_id:
        mantenimientos = mantenimientos.filter(vehiculo_id=vehiculo_id)
    
    estado = request.GET.get('estado')
    if estado:
        mantenimientos = mantenimientos.filter(estado=estado)
    
    tipo = request.GET.get('tipo')
    if tipo:
        mantenimientos = mantenimientos.filter(tipo_mantenimiento=tipo)
    
    fecha_desde = request.GET.get('fecha_desde')
    if fecha_desde:
        mantenimientos = mantenimientos.filter(fecha_programada__gte=fecha_desde)
    
    fecha_hasta = request.GET.get('fecha_hasta')
    if fecha_hasta:
        mantenimientos = mantenimientos.filter(fecha_programada__lte=fecha_hasta)
    
    # Paginación
    paginator = Paginator(mantenimientos, 20)
    page = request.GET.get('page')
    mantenimientos_page = paginator.get_page(page)
    
    # Opciones para filtros
    vehiculos = Vehiculo.objects.all()
    
    context = {
        'mantenimientos': mantenimientos_page,
        'vehiculos': vehiculos,
        'estados_mantenimiento': MantenimientoVehiculo.ESTADO_MANTENIMIENTO,
        'tipos_mantenimiento': MantenimientoVehiculo.TIPO_MANTENIMIENTO,
        'filtros': {
            'vehiculo': vehiculo_id,
            'estado': estado,
            'tipo': tipo,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    
    return render(request, 'flota/lista_mantenimientos.html', context)


@login_required
def completar_mantenimiento(request, mantenimiento_id):
    """Completar mantenimiento"""
    
    mantenimiento = get_object_or_404(
        MantenimientoVehiculo.objects.select_related('vehiculo'),
        id=mantenimiento_id
    )
    
    if request.method == 'POST':
        fecha_realizacion = request.POST.get('fecha_realizacion')
        kilometraje_actual = request.POST.get('kilometraje_actual')
        costo_mano_obra = request.POST.get('costo_mano_obra', 0)
        descripcion_trabajo = request.POST.get('descripcion_trabajo_realizado', '')
        
        if fecha_realizacion and kilometraje_actual:
            try:
                mantenimiento.fecha_fin = datetime.strptime(fecha_realizacion, '%Y-%m-%d')
                mantenimiento.kilometraje_actual = int(kilometraje_actual)
                mantenimiento.costo_mano_obra = float(costo_mano_obra)
                mantenimiento.trabajo_realizado = descripcion_trabajo
                mantenimiento.estado = 'completado'
                mantenimiento.save()
                
                # Actualizar el vehículo
                vehiculo = mantenimiento.vehiculo
                vehiculo.fecha_ultimo_mantenimiento = mantenimiento.fecha_fin.date()
                vehiculo.kilometraje_actual = mantenimiento.kilometraje_actual
                vehiculo.kilometraje_ultimo_mantenimiento = mantenimiento.kilometraje_actual
                vehiculo.save()
                
                messages.success(request, 'Mantenimiento completado exitosamente')
                return redirect('flota:detalle_mantenimiento', mantenimiento_id=mantenimiento.id)
                
            except ValueError as e:
                messages.error(request, f'Error en los datos: {str(e)}')
        else:
            messages.error(request, 'Fecha de realización y kilometraje actual son requeridos')
    
    context = {
        'mantenimiento': mantenimiento,
    }
    
    return render(request, 'flota/completar_mantenimiento.html', context)


@login_required
def detalle_mantenimiento(request, mantenimiento_id):
    """Detalle de mantenimiento"""
    
    mantenimiento = get_object_or_404(
        MantenimientoVehiculo.objects.select_related('vehiculo__tipo_vehiculo'),
        id=mantenimiento_id
    )
    
    # Repuestos utilizados
    repuestos_utilizados = mantenimiento.repuestos_utilizados.select_related('repuesto')
    
    # Calcular costo total
    costo_repuestos = repuestos_utilizados.aggregate(total=Sum('costo_total'))['total'] or 0
    costo_total = mantenimiento.costo_mano_obra + costo_repuestos
    
    context = {
        'mantenimiento': mantenimiento,
        'repuestos_utilizados': repuestos_utilizados,
        'costo_repuestos': costo_repuestos,
        'costo_total': costo_total,
    }
    
    return render(request, 'flota/detalle_mantenimiento.html', context)


@login_required
def lista_repuestos(request):
    """Lista de repuestos con filtros"""
    
    # Obtener repuestos con relaciones
    repuestos = RepuestoVehiculo.objects.all()
    
    # Filtros
    tipo_vehiculo = request.GET.get('tipo_vehiculo')
    if tipo_vehiculo:
        repuestos = repuestos.filter(tipo_vehiculo_id=tipo_vehiculo)
    
    bajo_stock = request.GET.get('bajo_stock')
    if bajo_stock == 'true':
        repuestos = repuestos.filter(cantidad_stock__lte=models.F('cantidad_minima'))
    
    # Búsqueda
    search = request.GET.get('search')
    if search:
        repuestos = repuestos.filter(
            Q(codigo__icontains=search) |
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(repuestos, 20)
    page = request.GET.get('page')
    repuestos_page = paginator.get_page(page)
    
    # Opciones para filtros
    # Estadísticas simples
    total_repuestos = RepuestoVehiculo.objects.count()
    stock_bajo = RepuestoVehiculo.objects.filter(cantidad_stock__lte=F('cantidad_minima')).count()
    # Valor total del stock
    valor_total = sum([r.valor_total_stock for r in RepuestoVehiculo.objects.all()])

    context = {
        'repuestos': repuestos_page,
        'estadisticas': {
            'total_repuestos': total_repuestos,
            'stock_bajo': stock_bajo,
            'valor_total': valor_total,
            'stock_optimo': max(total_repuestos - stock_bajo, 0),
        },
        'filtros': {
            'tipo_vehiculo': tipo_vehiculo,
            'bajo_stock': bajo_stock,
            'search': search,
        }
    }
    
    return render(request, 'flota/inventario_repuestos.html', context)


@login_required
def actualizar_stock_repuesto(request, repuesto_id):
    """Actualizar stock de repuesto"""
    
    repuesto = get_object_or_404(RepuestoVehiculo, id=repuesto_id)
    
    if request.method == 'POST':
        cantidad = request.POST.get('cantidad')
        tipo = request.POST.get('tipo')  # 'sumar' o 'restar'
        
        if cantidad and tipo:
            try:
                cantidad = int(cantidad)
                if tipo == 'sumar':
                    repuesto.cantidad_stock += cantidad
                    mensaje = f'Stock incrementado en {cantidad} unidades'
                elif tipo == 'restar':
                    if repuesto.cantidad_stock < cantidad:
                        messages.error(request, 'Stock insuficiente')
                        return redirect('flota:actualizar_stock_repuesto', repuesto_id=repuesto.id)
                    repuesto.cantidad_stock -= cantidad
                    mensaje = f'Stock decrementado en {cantidad} unidades'
                else:
                    messages.error(request, 'Tipo de operación inválido')
                    return redirect('flota:actualizar_stock_repuesto', repuesto_id=repuesto.id)
                
                repuesto.save()
                messages.success(request, mensaje)
                return redirect('flota:lista_repuestos')
                
            except ValueError:
                messages.error(request, 'Cantidad debe ser un número válido')
        else:
            messages.error(request, 'Cantidad y tipo de operación son requeridos')
    
    context = {
        'repuesto': repuesto,
    }
    
    return render(request, 'flota/actualizar_stock_repuesto.html', context)
