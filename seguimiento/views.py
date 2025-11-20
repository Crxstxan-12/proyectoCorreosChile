from django.shortcuts import render
from django.http import HttpResponse
import csv
from django.core.paginator import Paginator
from django.db.models import Q
from .models import EventoSeguimiento
from envios.models import Envio
import json
from django.utils import timezone

def index(request):
    saved_event = False
    saved_event_error = ''
    if request.method == 'POST' and request.POST.get('action') == 'nuevo_evento':
        envio_codigo = (request.POST.get('envio_codigo') or '').strip()
        estado = (request.POST.get('estado') or '').strip()
        ubicacion = (request.POST.get('ubicacion') or '').strip()
        observacion = (request.POST.get('observacion') or '').strip()
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        try:
            envio = Envio.objects.get(codigo=envio_codigo)
            estados_validos = [e[0] for e in EventoSeguimiento.ESTADOS]
            if estado not in estados_validos:
                raise ValueError('Estado inválido')
            ev = EventoSeguimiento(envio=envio, estado=estado, ubicacion=ubicacion, observacion=observacion)
            if lat and lng:
                ev.lat = lat
                ev.lng = lng
            ev.save()
            saved_event = True
        except Exception as e:
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
