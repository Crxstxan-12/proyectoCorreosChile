from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import csv
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import Envio, Bulto
from seguimiento.models import EventoSeguimiento
from django.urls import reverse

def index(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    origen = request.GET.get('origen', '').strip()
    destino = request.GET.get('destino', '').strip()

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
        'total_envios': Envio.objects.count(),
        'envios_pendientes': counts.get('pendiente', 0),
        'envios_transito': counts.get('en_transito', 0),
        'envios_entregados': counts.get('entregado', 0),
        'envios_devueltos': counts.get('devuelto', 0),
        'envios_cancelados': counts.get('cancelado', 0),
    }
    return render(request, 'envios/index.html', ctx)

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
        return JsonResponse({'ok': False, 'error': 'Falta envío'}, status=400)
    if not codigos:
        return JsonResponse({'ok': False, 'error': 'Sin códigos'}, status=400)
    try:
        envio = Envio.objects.get(codigo=envio_codigo)
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
    return JsonResponse({
        'ok': True,
        'envio_codigo': envio.codigo,
        'total': len(codigos),
        'creados': creados,
        'marcados_entregados': marcados,
        'estado_envio': envio.estado,
    })

def reporte_pdf(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    origen = request.GET.get('origen', '').strip()
    destino = request.GET.get('destino', '').strip()
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
    queryset = queryset.order_by('-creado_en')
    ctx = {
        'envios': queryset,
        'q': q,
        'estado': estado,
        'origen': origen,
        'destino': destino,
        'fecha': timezone.now(),
    }
    return render(request, 'envios/report.html', ctx)
