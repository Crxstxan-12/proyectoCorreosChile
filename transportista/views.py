from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Transportista
from django.contrib.auth.decorators import login_required
from usuarios.models import Perfil

@login_required
def index(request):
    permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador','editor']).exists()
    if not permitido:
        return redirect('usuarios:index')
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    queryset = Transportista.objects.all()
    if q:
        queryset = queryset.filter(Q(nombre__icontains=q) | Q(rut__icontains=q))
    if estado == 'activo':
        queryset = queryset.filter(activo=True)
    elif estado == 'inactivo':
        queryset = queryset.filter(activo=False)

    queryset = queryset.order_by('nombre')
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    ctx = {
        'transportistas': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'estado': estado,
        'total': Transportista.objects.count(),
        'activos': Transportista.objects.filter(activo=True).count(),
        'inactivos': Transportista.objects.filter(activo=False).count(),
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
