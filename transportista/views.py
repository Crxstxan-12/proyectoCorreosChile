from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Transportista
from django.contrib.auth.decorators import login_required
from usuarios.models import Perfil

@login_required
def index(request):
    permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    queryset = Transportista.objects.all()
    if q:
        queryset = queryset.filter(Q(nombre__icontains=q) | Q(rut__icontains=q))
    if estado == 'activo':
        queryset = queryset.filter(activo=True)
    elif estado == 'inactivo':
        queryset = queryset.filter(activo=False)

    queryset = queryset.order_by('-activo','nombre')
    try:
        per_page = int(request.GET.get('per_page') or 10)
    except Exception:
        per_page = 10
    if per_page not in [10, 20, 50, 100]:
        per_page = 10
    # Exportaciones
    if request.GET.get('export') == 'csv':
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transportistas.csv"'
        import csv
        writer = csv.writer(response)
        writer.writerow(['nombre','rut','tipo','email','telefono','estado'])
        for t in queryset:
            writer.writerow([t.nombre, t.rut, t.tipo, (t.email or ''), (t.telefono or ''), ('activo' if t.activo else 'inactivo')])
        return response
    if request.GET.get('export') == 'xls':
        from django.http import HttpResponse
        rows = [
            '<table border="1">',
            '<thead><tr><th>Nombre</th><th>RUT</th><th>Tipo</th><th>Email</th><th>Teléfono</th><th>Estado</th></tr></thead>',
            '<tbody>'
        ]
        for t in queryset:
            rows.append(f"<tr><td>{t.nombre}</td><td>{t.rut}</td><td>{t.tipo}</td><td>{t.email or ''}</td><td>{t.telefono or ''}</td><td>{'Activo' if t.activo else 'Inactivo'}</td></tr>")
        rows.append('</tbody></table>')
        html = '\n'.join(rows)
        response = HttpResponse(html, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="transportistas.xls"'
        return response
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    ctx = {
        'transportistas': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'estado': estado,
        'per_page': per_page,
        'total': Transportista.objects.count(),
        'activos': Transportista.objects.filter(activo=True).count(),
        'inactivos': Transportista.objects.filter(activo=False).count(),
        'permitido': permitido,
    }
    return render(request, 'transportista/index.html', ctx)

@login_required
def crear(request):
    if request.method == 'POST':
        permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
        if not permitido:
            return redirect('transportista:index')
        nombre = (request.POST.get('nombre') or '').strip()
        rut = (request.POST.get('rut') or '').strip()
        tipo = (request.POST.get('tipo') or '').strip() or 'empresa'
        email = (request.POST.get('email') or '').strip() or None
        telefono = (request.POST.get('telefono') or '').strip() or None
        direccion = (request.POST.get('direccion') or '').strip() or None
        activo = bool(request.POST.get('activo'))
        Transportista.objects.create(
            nombre=nombre, rut=rut, tipo=tipo, email=email, telefono=telefono, direccion=direccion, activo=activo
        )
        return redirect('transportista:index')
    return render(request, 'transportista/form.html', {'t': None, 'tipos': [x[0] for x in Transportista.TIPOS]})

@login_required
def editar(request, pk):
    t = get_object_or_404(Transportista, pk=pk)
    if request.method == 'POST':
        permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
        if not permitido:
            return redirect('transportista:index')
        t.nombre = (request.POST.get('nombre') or '').strip()
        t.rut = (request.POST.get('rut') or '').strip()
        t.tipo = (request.POST.get('tipo') or '').strip() or 'empresa'
        t.email = (request.POST.get('email') or '').strip() or None
        t.telefono = (request.POST.get('telefono') or '').strip() or None
        t.direccion = (request.POST.get('direccion') or '').strip() or None
        t.activo = bool(request.POST.get('activo'))
        t.save()
        return redirect('transportista:index')
    return render(request, 'transportista/form.html', {'t': t, 'tipos': [x[0] for x in Transportista.TIPOS]})

@login_required
def toggle(request, pk):
    t = get_object_or_404(Transportista, pk=pk)
    if request.method == 'POST':
        permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
        if not permitido:
            return redirect('transportista:index')
        t.activo = not t.activo
        t.save()
    return redirect('transportista:index')
