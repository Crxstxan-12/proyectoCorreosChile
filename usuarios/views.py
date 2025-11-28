from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from .models import Perfil
from django.db.models import Case, When, IntegerField
from envios.models import Envio
from seguimiento.models import EventoSeguimiento
from notificaciones.models import Notificacion
from reclamos.models import Reclamo
from transportista.models import Transportista
from ecommerce.models import PedidoEcommerce
from django.utils import timezone

@login_required
def index(request):
    if not request.user.is_authenticated:
        return redirect('usuarios:login')
    saved_role = False
    error_role = ''
    perfil_req = Perfil.objects.filter(user=request.user).first()
    es_admin = bool(perfil_req and perfil_req.rol == 'administrador')
    if request.method == 'POST' and request.POST.get('action') == 'set_rol':
        if not es_admin:
            error_role = 'Sin permisos'
        else:
            try:
                uid = int(request.POST.get('user_id'))
                rol = (request.POST.get('rol') or '').strip()
                if rol not in ['administrador','editor','usuario']:
                    raise ValueError('Rol inválido')
                from django.contrib.auth.models import User
                u = User.objects.get(id=uid)
                p, _ = Perfil.objects.get_or_create(user=u)
                p.rol = rol
                p.save()
                saved_role = True
            except Exception:
                error_role = 'Error al actualizar rol'
    role_order = Case(
        When(rol='administrador', then=0),
        When(rol='editor', then=1),
        When(rol='usuario', then=2),
        default=3,
        output_field=IntegerField()
    )
    perfiles = (
        Perfil.objects.select_related('user')
        .annotate(role_order=role_order)
        .order_by('role_order', 'user__username')
    )
    return render(request, 'usuarios/index.html', {'perfiles': perfiles, 'saved_role': saved_role, 'error_role': error_role, 'es_admin': es_admin})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuario', 'autocomplete': 'username'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña', 'autocomplete': 'current-password'})
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('usuarios:index')
    else:
        form = AuthenticationForm(request)
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuario', 'autocomplete': 'username'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña', 'autocomplete': 'current-password'})
    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('usuarios:login')

@login_required
def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('usuarios:login')
    total_envios = Envio.objects.count()
    envios_entregados = Envio.objects.filter(estado='entregado').count()
    envios_transito = Envio.objects.filter(estado='en_transito').count()
    reclamos_abiertos = Reclamo.objects.filter(estado='abierto').count()
    notif_no_leidas = Notificacion.objects.filter(usuario=request.user, leida=False).count()
    transportistas_activos = Transportista.objects.filter(activo=True).count()
    pedidos_ecommerce = PedidoEcommerce.objects.count()
    pedidos_pendientes = PedidoEcommerce.objects.filter(estado='pendiente').count()
    ult_envios = Envio.objects.only('codigo','estado','origen','destino','creado_en').order_by('-creado_en')[:5]
    metricas = {
        'Envíos': total_envios,
        'En tránsito': envios_transito,
        'Entregados': envios_entregados,
        'Reclamos abiertos': reclamos_abiertos,
        'Notificaciones sin leer': notif_no_leidas,
        'Transportistas activos': transportistas_activos,
        'Pedidos E-commerce': pedidos_ecommerce,
        'Pedidos Pendientes': pedidos_pendientes,
    }
    perfil = Perfil.objects.filter(user=request.user).first()
    es_admin_editor = bool(perfil and perfil.rol in ['administrador','editor'])
    return render(
        request,
        'dashboard.html',
        {
            'metricas': metricas,
            'ult_envios': ult_envios,
            'es_admin_editor': es_admin_editor,
        },
    )

def funcionalidades_pdf(request):
    if not request.user.is_authenticated:
        return redirect('usuarios:login')
    return render(request, 'usuarios/funcionalidades.html', {'fecha': timezone.now()})

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        # Estilizar campos
        for name, field in form.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
        if form.is_valid():
            user = form.save()
            user.email = (request.POST.get('email') or '').strip()
            user.first_name = (request.POST.get('first_name') or '').strip()
            user.last_name = (request.POST.get('last_name') or '').strip()
            user.save()
            login(request, user)
            return redirect('usuarios:dashboard')
    else:
        form = UserCreationForm()
        for name, field in form.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
    return render(request, 'usuarios/register.html', {'form': form})

