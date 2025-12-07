from django.shortcuts import render
from django.http import HttpResponse
import csv
from django.core.paginator import Paginator
from django.db.models import Q
from .models import EventoSeguimiento
from envios.models import Envio
import json
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from usuarios.models import Perfil
from django.db import connection
from envios.eta import recompute_eta_for_envio

def _ensure_evento_foto_column():
    try:
        with connection.cursor() as c:
            c.execute("SHOW COLUMNS FROM seguimiento_eventoseguimiento LIKE %s", ['foto_url'])
            row = c.fetchone()
            if not row:
                c.execute("ALTER TABLE seguimiento_eventoseguimiento ADD COLUMN foto_url VARCHAR(255) NULL")
    except Exception:
        pass

@login_required
def index(request):
    _ensure_evento_foto_column()
    saved_event = False
    saved_event_error = ''
    if request.method == 'POST' and request.POST.get('action') == 'nuevo_evento':
        envio_codigo = (request.POST.get('envio_codigo') or '').strip()
        estado = (request.POST.get('estado') or '').strip()
        ubicacion = (request.POST.get('ubicacion') or '').strip()
        observacion = (request.POST.get('observacion') or '').strip()
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        receptor = (request.POST.get('receptor') or '').strip()
        foto_url = (request.POST.get('foto_url') or '').strip()
        foto_file = request.FILES.get('foto')
        try:
            if not envio_codigo:
                raise ValueError('Falta código de envío')
            envio = Envio.objects.get(codigo=envio_codigo)
            permitido_admin = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
            permitido_duenio = (getattr(envio, 'usuario', None) == request.user)
            if not (permitido_admin or permitido_duenio):
                raise ValueError('Sin permisos para registrar eventos en este envío')
            estados_validos = [e[0] for e in EventoSeguimiento.ESTADOS]
            if estado not in estados_validos:
                raise ValueError('Estado inválido')
            # Agregar receptor a observación si viene
            obs_final = observacion
            if receptor:
                obs_final = (observacion + f" | Receptor: {receptor}").strip()
            ev = EventoSeguimiento(envio=envio, estado=estado, ubicacion=ubicacion, observacion=obs_final)
            # Resolver evidencia fotográfica
            evidencia_url = ''
            if foto_file and hasattr(settings, 'MEDIA_ROOT'):
                import time
                fname = f"entregas/{envio.codigo}_{int(time.time())}.jpg"
                path = default_storage.save(fname, ContentFile(foto_file.read()))
                evidencia_url = default_storage.url(path)
            elif foto_url:
                evidencia_url = foto_url
            if evidencia_url:
                ev.foto_url = evidencia_url
            if lat and lng:
                ev.lat = lat
                ev.lng = lng
            ev.save()
            # Recalcular ETA si hay coordenadas
            try:
                if lat and lng:
                    eta = recompute_eta_for_envio(envio, float(lat), float(lng))
                    if eta:
                        from notificaciones.models import Notificacion
                        Notificacion.objects.create(
                            titulo=f"ETA actualizado: {envio.codigo}",
                            mensaje=f"Nueva hora estimada: {envio.fecha_estimada_entrega.strftime('%d/%m %H:%M')} (restante ~{envio.eta_km_restante} km)",
                            tipo='info',
                            canal='web',
                            usuario=getattr(envio, 'usuario', None)
                        )
            except Exception:
                pass
            # Si se confirma entrega, actualizar envío y bultos y guardar evidencia
            if estado == 'entregado':
                if envio.estado != 'entregado':
                    envio.estado = 'entregado'
                    envio.save(update_fields=['estado','actualizado_en'])
                try:
                    from envios.models import Bulto
                    for b in envio.bultos.all():
                        b.entregado = True
                        b.entregado_en = timezone.now()
                        if evidencia_url:
                            b.foto_url = evidencia_url
                        b.save()
                except Exception:
                    pass
            saved_event = True
        except Envio.DoesNotExist:
            saved_event_error = 'Envío no encontrado'
        except ValueError as e:
            saved_event_error = str(e)
        except Exception:
            saved_event_error = 'Error al registrar el evento'
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()

    queryset = EventoSeguimiento.objects.select_related('envio')
    if q:
        queryset = queryset.filter(
            Q(envio__codigo__icontains=q) |
            Q(ubicacion__icontains=q) |
            Q(observacion__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if desde:
        queryset = queryset.filter(registrado_en__date__gte=desde)
    if hasta:
        queryset = queryset.filter(registrado_en__date__lte=hasta)

    queryset = queryset.order_by('-registrado_en')

    map_points = []
    for ev in queryset:
        if ev.lat is not None and ev.lng is not None:
            map_points.append({
                'lat': float(ev.lat),
                'lng': float(ev.lng),
                'label': f"{getattr(ev.envio,'codigo','')} - {ev.estado}"
            })

    if request.GET.get('export') == 'xls':
        rows = [
            '<table border="1">',
            '<thead><tr><th>codigo_envio</th><th>estado</th><th>ubicacion</th><th>observacion</th><th>registrado_en</th></tr></thead>',
            '<tbody>'
        ]
        for ev in queryset:
            rows.append(
                f"<tr><td>{getattr(ev.envio,'codigo','')}</td><td>{getattr(ev,'estado','')}</td><td>{getattr(ev,'ubicacion','')}</td><td>{getattr(ev,'observacion','')}</td><td>{getattr(ev,'registrado_en','')}</td></tr>"
            )
        rows.append('</tbody></table>')
        html = '\n'.join(rows)
        response = HttpResponse(html, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="seguimiento.xls"'
        return response

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="seguimiento.csv"'
        writer = csv.writer(response)
        writer.writerow(['codigo_envio','estado','ubicacion','observacion','registrado_en'])
        for ev in queryset:
            writer.writerow([getattr(ev.envio,'codigo',''), getattr(ev,'estado',''), getattr(ev,'ubicacion',''), getattr(ev,'observacion',''), getattr(ev,'registrado_en','')])
        return response

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    estados = [e[0] for e in EventoSeguimiento.ESTADOS]
    counts = {k: EventoSeguimiento.objects.filter(estado=k).count() for k in estados}

    ctx = {
        'eventos': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'estado': estado,
        'desde': desde,
        'hasta': hasta,
        'total_eventos': EventoSeguimiento.objects.count(),
        'ev_pendiente': counts.get('pendiente', 0),
        'ev_transito': counts.get('en_transito', 0),
        'ev_planta': counts.get('en_planta', 0),
        'ev_reparto': counts.get('en_reparto', 0),
        'ev_entregado': counts.get('entregado', 0),
        'ev_incidencia': counts.get('incidencia', 0),
        'map_points_json': json.dumps(map_points),
        'estados_all': estados,
        'saved_event': saved_event,
        'saved_event_error': saved_event_error,
    }
    return render(request, 'seguimiento/index.html', ctx)

@login_required
def reporte_pdf(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()

    queryset = EventoSeguimiento.objects.select_related('envio')
    if q:
        queryset = queryset.filter(
            Q(envio__codigo__icontains=q) |
            Q(ubicacion__icontains=q) |
            Q(observacion__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if desde:
        queryset = queryset.filter(registrado_en__date__gte=desde)
    if hasta:
        queryset = queryset.filter(registrado_en__date__lte=hasta)

    queryset = queryset.order_by('-registrado_en')

    ctx = {
        'eventos': queryset,
        'q': q,
        'estado': estado,
        'desde': desde,
        'hasta': hasta,
        'fecha': timezone.now(),
    }
    return render(request, 'seguimiento/report.html', ctx)


def api_estado_envio(request, codigo):
    """Devuelve estado actual y últimos eventos de un envío por código (JSON)"""
    try:
        envio = Envio.objects.get(codigo=codigo)
        eventos = EventoSeguimiento.objects.filter(envio=envio).order_by('-registrado_en')[:10]
        data = {
            'codigo': envio.codigo,
            'estado': envio.estado,
            'destinatario': envio.destinatario_nombre,
            'direccion_destino': envio.direccion_destino,
            'transportista': getattr(envio.transportista, 'nombre', None),
            'eta': envio.fecha_estimada_entrega.isoformat() if getattr(envio, 'fecha_estimada_entrega', None) else None,
            'eta_km_restante': float(envio.eta_km_restante) if getattr(envio, 'eta_km_restante', None) else None,
            'eventos': [
                {
                    'estado': ev.estado,
                    'ubicacion': ev.ubicacion,
                    'observacion': ev.observacion,
                    'registrado_en': ev.registrado_en.isoformat(),
                    'lat': float(ev.lat) if ev.lat is not None else None,
                    'lng': float(ev.lng) if ev.lng is not None else None,
                } for ev in eventos
            ]
        }
        return JsonResponse(data)
    except Envio.DoesNotExist:
        return JsonResponse({'error': 'envio_no_encontrado'}, status=404)
