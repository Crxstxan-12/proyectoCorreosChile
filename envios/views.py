from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import csv
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from .models import Envio, Bulto
from .eta import recompute_eta_for_envio
from seguimiento.models import EventoSeguimiento
from django.urls import reverse
from transportista.models import Transportista
from django.contrib.auth.decorators import login_required
from usuarios.models import Perfil
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

@login_required
def index(request):
    assigned = False
    assigned_error = ''
    eta_saved = False
    eta_error = ''
    if request.method == 'POST' and request.POST.get('action') == 'assign_transportista':
        envio_codigo = (request.POST.get('envio_codigo') or '').strip()
        transportista_id = request.POST.get('transportista_id')
        try:
            envio = Envio.objects.get(codigo=envio_codigo)
            es_admin = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
            es_duenio = (getattr(envio, 'usuario', None) == request.user)
            if not (es_admin or es_duenio):
                raise Exception('Sin permisos')
            t = Transportista.objects.get(id=int(transportista_id), activo=True)
            envio.transportista = t
            envio.save()
            assigned = True
        except Envio.DoesNotExist:
            assigned_error = 'Envío no encontrado'
        except Transportista.DoesNotExist:
            assigned_error = 'Transportista no válido'
        except Exception:
            assigned_error = 'Error al asignar transportista'
    elif request.method == 'POST' and request.POST.get('action') == 'set_eta':
        from django.utils import timezone
        from datetime import datetime
        try:
            envio_codigo = (request.POST.get('envio_codigo') or '').strip()
            fecha = (request.POST.get('fecha_estimada') or '').strip()
            hora = (request.POST.get('hora_estimada') or '').strip()
            if not envio_codigo or not fecha:
                raise ValueError('Faltan datos')
            envio = Envio.objects.get(codigo=envio_codigo)
            permitido_admin = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
            permitido_duenio = (getattr(envio, 'usuario', None) == request.user)
            if not (permitido_admin or permitido_duenio):
                raise ValueError('Sin permisos')
            dt_str = fecha + (' ' + hora if hora else ' 12:00')
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            envio.fecha_estimada_entrega = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            envio.eta_actualizado_en = timezone.now()
            envio.save(update_fields=['fecha_estimada_entrega','eta_actualizado_en','actualizado_en'])
            eta_saved = True
        except Envio.DoesNotExist:
            eta_error = 'Envío no encontrado'
        except ValueError as e:
            eta_error = str(e)
        except Exception:
            eta_error = 'Error al guardar ETA'
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    origen = request.GET.get('origen', '').strip()
    destino = request.GET.get('destino', '').strip()
    transportista_id = request.GET.get('transportista_id', '').strip()

    queryset = Envio.objects.all()
    if q:
        queryset = queryset.filter(
            Q(codigo__icontains=q) |
            Q(destinatario_nombre__icontains=q) |
            Q(direccion_destino__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if origen:
        queryset = queryset.filter(origen__icontains=origen)
    if destino:
        queryset = queryset.filter(destino__icontains=destino)
    if transportista_id:
        queryset = queryset.filter(transportista_id=transportista_id)

    queryset = queryset.order_by('-creado_en')

    if request.GET.get('export') == 'xls':
        rows = [
            '<table border="1">',
            '<thead><tr><th>codigo</th><th>estado</th><th>origen</th><th>destino</th><th>destinatario</th><th>bultos</th><th>peso_kg</th><th>costo</th><th>creado_en</th></tr></thead>',
            '<tbody>'
        ]
        for e in queryset:
            rows.append(
                f"<tr><td>{getattr(e,'codigo','')}</td><td>{getattr(e,'estado','')}</td><td>{getattr(e,'origen','')}</td><td>{getattr(e,'destino','')}</td><td>{getattr(e,'destinatario_nombre','')}</td><td>{e.bultos.count()}</td><td>{getattr(e,'peso_kg','')}</td><td>{getattr(e,'costo','')}</td><td>{getattr(e,'creado_en','')}</td></tr>"
            )
        rows.append('</tbody></table>')
        html = '\n'.join(rows)
        response = HttpResponse(html, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="envios.xls"'
        return response

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="envios.csv"'
        writer = csv.writer(response)
        writer.writerow(['codigo','estado','origen','destino','destinatario','peso_kg','costo','creado_en'])
        for e in queryset:
            writer.writerow([getattr(e,'codigo',''), getattr(e,'estado',''), getattr(e,'origen',''), getattr(e,'destino',''), getattr(e,'destinatario_nombre',''), getattr(e,'peso_kg',''), getattr(e,'costo',''), getattr(e,'creado_en','')])
        return response

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    estados = [e[0] for e in Envio.ESTADOS]
    counts = {k: Envio.objects.filter(estado=k).count() for k in estados}

    ctx = {
        'envios': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'estado': estado,
        'origen': origen,
        'destino': destino,
        'transportista_id': transportista_id,
        'total_envios': Envio.objects.count(),
        'envios_pendientes': counts.get('pendiente', 0),
        'envios_transito': counts.get('en_transito', 0),
        'envios_entregados': counts.get('entregado', 0),
        'envios_devueltos': counts.get('devuelto', 0),
        'envios_cancelados': counts.get('cancelado', 0),
        'transportistas': Transportista.objects.filter(activo=True).order_by('nombre'),
        'assigned': assigned,
        'assigned_error': assigned_error,
        'eta_saved': eta_saved,
        'eta_error': eta_error,
    }
    return render(request, 'envios/index.html', ctx)

@login_required
def scan_bultos(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)
    payload = {}
    if request.headers.get('Content-Type', '').startswith('application/json'):
        import json
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
    else:
        payload = {
            'envio_codigo': request.POST.get('envio_codigo', '').strip(),
            'codigos_text': request.POST.get('codigos_text', '').strip(),
        }
    envio_codigo = (payload.get('envio_codigo') or '').strip()
    codigos = payload.get('codigos')
    lat = payload.get('lat')
    lng = payload.get('lng')
    ubicacion_payload = payload.get('ubicacion')
    if not codigos:
        codigos_text = (payload.get('codigos_text') or '').strip()
        codigos = [c.strip() for c in codigos_text.replace('\r', '\n').split('\n') if c.strip()]
    if not envio_codigo:
        # Intentar inferir envío desde el primer código de barras (formato EC-...-SKU-#)
        if codigos:
            first = codigos[0]
            try:
                # Si existe el bulto, usar su envío
                b = Bulto.objects.filter(codigo_barras=first).select_related('envio').first()
                if b:
                    envio_codigo = b.envio.codigo
                else:
                    # Inferir prefijo hasta el segundo guión
                    parts = first.split('-')
                    if len(parts) >= 3:
                        envio_codigo = '-'.join(parts[:2]) if parts[0].startswith('EC') else parts[0]
            except Exception:
                envio_codigo = None
        if not envio_codigo:
            return JsonResponse({'ok': False, 'error': 'Falta envío'}, status=400)
    if not codigos:
        return JsonResponse({'ok': False, 'error': 'Sin códigos'}, status=400)
    try:
        envio = Envio.objects.get(codigo=envio_codigo)
        permitido_admin = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
        permitido_duenio = (getattr(envio, 'usuario', None) == request.user)
        if not (permitido_admin or permitido_duenio):
            return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    except Envio.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Envío no encontrado'}, status=404)
    creados = 0
    marcados = 0
    for code in codigos:
        bulto, created = Bulto.objects.get_or_create(envio=envio, codigo_barras=code)
        if created:
            creados += 1
        if not bulto.entregado:
            bulto.entregado = True
            bulto.entregado_en = timezone.now()
            bulto.save()
            marcados += 1
    if envio.bultos.exists() and not envio.bultos.filter(entregado=False).exists():
        if envio.estado != 'entregado':
            envio.estado = 'entregado'
            envio.save()
            ev_kwargs = {'envio': envio, 'estado': 'entregado', 'ubicacion': (ubicacion_payload or 'Entrega'), 'observacion': 'Multibultos entregados'}
            if lat and lng:
                ev_kwargs['lat'] = lat
                ev_kwargs['lng'] = lng
            EventoSeguimiento.objects.create(**ev_kwargs)
    # Recalcular ETA si se envía ubicación
    eta_resp = None
    try:
        if lat and lng:
            res = recompute_eta_for_envio(envio, float(lat), float(lng))
            if res:
                eta_dt, km = res
                eta_resp = {
                    'eta': eta_dt.isoformat(),
                    'eta_label': eta_dt.strftime('%d/%m %H:%M'),
                    'km_restante': round(km, 2),
                }
    except Exception:
        eta_resp = None
    return JsonResponse({
        'ok': True,
        'envio_codigo': envio.codigo,
        'total': len(codigos),
        'creados': creados,
        'marcados_entregados': marcados,
        'estado_envio': envio.estado,
        'eta': eta_resp,
    })


@login_required
def confirmar_entrega_multibulto(request):
    """Confirma entrega de todos los bultos de un envío con una sola evidencia (foto_url)
    Soporta JSON o formulario. Opcionales: receptor, observacion, lat, lng, ubicacion.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)
    try:
        permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
        if not permitido:
            return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
        if request.headers.get('Content-Type','').startswith('application/json'):
            import json
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST
        foto_file = request.FILES.get('foto')
        envio_codigo = (payload.get('envio_codigo') or '').strip()
        codigo_bulto = (payload.get('codigo_bulto') or '').strip()
        foto_url = (payload.get('foto_url') or '').strip()
        receptor = (payload.get('receptor') or '').strip()
        observacion = (payload.get('observacion') or '').strip()
        lat = payload.get('lat')
        lng = payload.get('lng')
        ubicacion_payload = payload.get('ubicacion')
        envio = None
        if envio_codigo:
            envio = Envio.objects.get(codigo=envio_codigo)
        elif codigo_bulto:
            b = Bulto.objects.filter(codigo_barras=codigo_bulto).select_related('envio').first()
            if b:
                envio = b.envio
        if not envio:
            return JsonResponse({'ok': False, 'error': 'Envío no encontrado'}, status=404)
        # Marcar todos los bultos como entregados y guardar evidencia
        total_bultos = envio.bultos.count()
        marcados = 0
        # Guardar evidencia si viene archivo
        if foto_file and hasattr(settings, 'MEDIA_ROOT'):
            import time
            fname = f"entregas/{envio.codigo}_{int(time.time())}.jpg"
            path = default_storage.save(fname, ContentFile(foto_file.read()))
            foto_url = default_storage.url(path)
        for b in envio.bultos.all():
            b.entregado = True
            b.entregado_en = timezone.now()
            if foto_url:
                b.foto_url = foto_url
            b.save()
            marcados += 1
        # Actualizar estado del envío y registrar evento
        if envio.estado != 'entregado':
            envio.estado = 'entregado'
            envio.save(update_fields=['estado','actualizado_en'])
            ev_kwargs = {
                'envio': envio,
                'estado': 'entregado',
                'ubicacion': (ubicacion_payload or 'Entrega'),
                'observacion': observacion or (f'Entrega multibulto ({total_bultos})')
            }
            if lat and lng:
                ev_kwargs['lat'] = lat
                ev_kwargs['lng'] = lng
            EventoSeguimiento.objects.create(**ev_kwargs)
        return JsonResponse({'ok': True, 'envio_codigo': envio.codigo, 'bultos_total': total_bultos, 'marcados': marcados})
    except Envio.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Envío no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)

@login_required
def reporte_pdf(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    origen = request.GET.get('origen', '').strip()
    destino = request.GET.get('destino', '').strip()
    transportista_id = request.GET.get('transportista_id', '').strip()
    queryset = Envio.objects.all()
    if q:
        queryset = queryset.filter(
            Q(codigo__icontains=q) |
            Q(destinatario_nombre__icontains=q) |
            Q(direccion_destino__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if origen:
        queryset = queryset.filter(origen__icontains=origen)
    if destino:
        queryset = queryset.filter(destino__icontains=destino)
    if transportista_id:
        queryset = queryset.filter(transportista_id=transportista_id)
    queryset = queryset.order_by('-creado_en')
    tp_nombre = '-'
    if transportista_id:
        try:
            tp = Transportista.objects.get(id=int(transportista_id))
            tp_nombre = tp.nombre
        except Exception:
            tp_nombre = '-'
    ctx = {
        'envios': queryset,
        'q': q,
        'estado': estado,
        'origen': origen,
        'destino': destino,
        'transportista_id': transportista_id,
        'transportista_nombre': tp_nombre,
        'fecha': timezone.now(),
    }
    return render(request, 'envios/report.html', ctx)


@login_required
def reportes_operacionales(request):
    """Reporte operacional con métricas por sucursal (origen) y transportista, exportable CSV/XLS/PDF"""
    desde = (request.GET.get('desde') or '').strip()
    hasta = (request.GET.get('hasta') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    transportista_id = (request.GET.get('transportista_id') or '').strip()

    qs = Envio.objects.all()
    if desde:
        qs = qs.filter(creado_en__date__gte=desde)
    if hasta:
        qs = qs.filter(creado_en__date__lte=hasta)
    if estado:
        qs = qs.filter(estado=estado)
    if transportista_id:
        qs = qs.filter(transportista_id=transportista_id)

    # Métricas por sucursal (origen)
    por_origen = (
        qs.values('origen')
        .annotate(
            total=Count('id'),
            entregados=Count('id', filter=Q(estado='entregado')),
            transito=Count('id', filter=Q(estado='en_transito')),
            pendientes=Count('id', filter=Q(estado='pendiente')),
            cancelados=Count('id', filter=Q(estado='cancelado')),
        )
        .order_by('-total')
    )

    # Métricas por transportista
    por_transportista = (
        qs.values('transportista__nombre')
        .annotate(
            total=Count('id'),
            entregados=Count('id', filter=Q(estado='entregado')),
            transito=Count('id', filter=Q(estado='en_transito')),
            pendientes=Count('id', filter=Q(estado='pendiente')),
            cancelados=Count('id', filter=Q(estado='cancelado')),
        )
        .order_by('-total')
    )

    # Métricas de reclamos asociados en el rango
    try:
        from reclamos.models import Reclamo
        rec_qs = Reclamo.objects.all()
        if desde:
            rec_qs = rec_qs.filter(creado_en__date__gte=desde)
        if hasta:
            rec_qs = rec_qs.filter(creado_en__date__lte=hasta)
        if estado:
            # asociar por estado de envío si se filtró
            rec_qs = rec_qs.filter(envio__estado=estado)
        if transportista_id:
            rec_qs = rec_qs.filter(envio__transportista_id=transportista_id)
        recuento_reclamos = rec_qs.count()
    except Exception:
        recuento_reclamos = 0

    # Exportaciones
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reporte_operacional.csv"'
        writer = csv.writer(response)
        writer.writerow(['Filtro_desde', 'Filtro_hasta', 'Filtro_estado', 'Filtro_transportista_id'])
        writer.writerow([desde, hasta, estado, transportista_id])
        writer.writerow([]); writer.writerow(['Por sucursal (origen)'])
        writer.writerow(['origen','total','entregados','en_transito','pendientes','cancelados'])
        for r in por_origen:
            writer.writerow([r.get('origen') or '-', r['total'], r['entregados'], r['transito'], r['pendientes'], r['cancelados']])
        writer.writerow([]); writer.writerow(['Por transportista'])
        writer.writerow(['transportista','total','entregados','en_transito','pendientes','cancelados'])
        for r in por_transportista:
            writer.writerow([r.get('transportista__nombre') or '-', r['total'], r['entregados'], r['transito'], r['pendientes'], r['cancelados']])
        writer.writerow([]); writer.writerow(['reclamos_asociados', recuento_reclamos])
        return response

    if request.GET.get('export') == 'xls':
        rows = [
            '<table border="1">',
            f'<caption>Reporte Operacional - {timezone.now()}</caption>',
            '<thead><tr><th>Sección</th><th>Clave</th><th>Total</th><th>Entregados</th><th>En tránsito</th><th>Pendientes</th><th>Cancelados</th></tr></thead>',
            '<tbody>'
        ]
        for r in por_origen:
            rows.append(f"<tr><td>Sucursal</td><td>{r.get('origen') or '-'}</td><td>{r['total']}</td><td>{r['entregados']}</td><td>{r['transito']}</td><td>{r['pendientes']}</td><td>{r['cancelados']}</td></tr>")
        for r in por_transportista:
            rows.append(f"<tr><td>Transportista</td><td>{r.get('transportista__nombre') or '-'}</td><td>{r['total']}</td><td>{r['entregados']}</td><td>{r['transito']}</td><td>{r['pendientes']}</td><td>{r['cancelados']}</td></tr>")
        rows.append(f"<tr><td>Extra</td><td>Reclamos asociados</td><td>{recuento_reclamos}</td><td></td><td></td><td></td><td></td></tr>")
        rows.append('</tbody></table>')
        html = '\n'.join(rows)
        response = HttpResponse(html, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="reporte_operacional.xls"'
        return response

    ctx = {
        'desde': desde,
        'hasta': hasta,
        'estado': estado,
        'transportista_id': transportista_id,
        'por_origen': por_origen,
        'por_transportista': por_transportista,
        'recuentos': {'reclamos': recuento_reclamos},
        'fecha': timezone.now(),
        'transportistas': Transportista.objects.filter(activo=True).order_by('nombre'),
    }
    return render(request, 'envios/report_operacional.html', ctx)
