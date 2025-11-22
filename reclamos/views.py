from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
import csv
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Reclamo
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from usuarios.models import Perfil

@login_required
def index(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()

    queryset = Reclamo.objects.all()
    if q:
        queryset = queryset.filter(
            Q(numero__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(respuesta__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if desde:
        queryset = queryset.filter(creado_en__date__gte=desde)
    if hasta:
        queryset = queryset.filter(creado_en__date__lte=hasta)

    queryset = queryset.order_by('-creado_en')

    if request.GET.get('export') == 'xls':
        rows = [
            '<table border="1">',
            '<thead><tr><th>numero</th><th>tipo</th><th>estado</th><th>descripcion</th><th>creado_en</th></tr></thead>',
            '<tbody>'
        ]
        for r in queryset:
            rows.append(
                f"<tr><td>{getattr(r,'numero','')}</td><td class='text-capitalize'>{getattr(r,'tipo','')}</td><td>{getattr(r,'estado','')}</td><td>{getattr(r,'descripcion','')}</td><td>{getattr(r,'creado_en','')}</td></tr>"
            )
        rows.append('</tbody></table>')
        html = '\n'.join(rows)
        response = HttpResponse(html, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="reclamos.xls"'
        return response

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reclamos.csv"'
        writer = csv.writer(response)
        writer.writerow(['numero','tipo','estado','descripcion','creado_en'])
        for r in queryset:
            writer.writerow([getattr(r,'numero',''), getattr(r,'tipo',''), getattr(r,'estado',''), getattr(r,'descripcion',''), getattr(r,'creado_en','')])
        return response

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    estados = [e[0] for e in Reclamo.ESTADOS]
    tipos = [t[0] for t in Reclamo.TIPOS]
    counts_estado = {k: Reclamo.objects.filter(estado=k).count() for k in estados}
    counts_tipo = {k: Reclamo.objects.filter(tipo=k).count() for k in tipos}

    ctx = {
        'reclamos': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'estado': estado,
        'tipo': tipo,
        'desde': desde,
        'hasta': hasta,
        'total_reclamos': Reclamo.objects.count(),
        'rec_abiertos': counts_estado.get('abierto', 0),
        'rec_revision': counts_estado.get('en_revision', 0),
        'rec_resueltos': counts_estado.get('resuelto', 0),
        'rec_cerrados': counts_estado.get('cerrado', 0),
        'rec_perdida': counts_tipo.get('perdida', 0),
        'rec_danio': counts_tipo.get('danio', 0),
        'rec_retraso': counts_tipo.get('retraso', 0),
        'rec_otro': counts_tipo.get('otro', 0),
    }
    return render(request, 'reclamos/index.html', ctx)

@login_required
def detalle(request, pk):
    r = get_object_or_404(Reclamo, pk=pk)
    estados = [e[0] for e in Reclamo.ESTADOS]
    tipos = [t[0] for t in Reclamo.TIPOS]
    saved = False
    if request.method == 'POST':
        permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
        if not permitido:
            return redirect('reclamos:detalle', pk=r.id)
        nuevo_estado = (request.POST.get('estado') or '').strip()
        respuesta = (request.POST.get('respuesta') or '').strip() or None
        if nuevo_estado in estados:
            r.estado = nuevo_estado
        r.respuesta = respuesta
        r.save()
        saved = True
        return redirect('reclamos:detalle', pk=r.id)
    ctx = {
        'r': r,
        'estados': estados,
        'tipos': tipos,
        'saved': saved,
    }
    return render(request, 'reclamos/detalle.html', ctx)

@login_required
def reporte_pdf(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()

    queryset = Reclamo.objects.all()
    if q:
        queryset = queryset.filter(
            Q(numero__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(respuesta__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if desde:
        queryset = queryset.filter(creado_en__date__gte=desde)
    if hasta:
        queryset = queryset.filter(creado_en__date__lte=hasta)

    queryset = queryset.order_by('-creado_en')

    ctx = {
        'reclamos': queryset,
        'q': q,
        'estado': estado,
        'tipo': tipo,
        'desde': desde,
        'hasta': hasta,
        'fecha': timezone.now(),
    }
    return render(request, 'reclamos/report.html', ctx)
