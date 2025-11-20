from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .models import Perfil
from envios.models import Envio
from seguimiento.models import EventoSeguimiento
from notificaciones.models import Notificacion
from reclamos.models import Reclamo
from transportista.models import Transportista

def index(request):
    if not request.user.is_authenticated:
        return redirect('usuarios:login')
    perfiles = Perfil.objects.select_related('user').all().order_by('user__username')
    return render(request, 'usuarios/index.html', {'perfiles': perfiles})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuario', 'autocomplete': 'username'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña', 'autocomplete': 'current-password'})
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('usuarios:dashboard')
    else:
        form = AuthenticationForm(request)
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuario', 'autocomplete': 'username'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña', 'autocomplete': 'current-password'})
    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('usuarios:login')

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('usuarios:login')
    total_envios = Envio.objects.count()
    envios_entregados = Envio.objects.filter(estado='entregado').count()
    envios_transito = Envio.objects.filter(estado='en_transito').count()
    reclamos_abiertos = Reclamo.objects.filter(estado='abierto').count()
    notif_no_leidas = Notificacion.objects.filter(usuario=request.user, leida=False).count()
    transportistas_activos = Transportista.objects.filter(activo=True).count()
    ult_envios = Envio.objects.all().order_by('-creado_en')[:5]
    return render(
        request,
        'dashboard.html',
        {
            'total_envios': total_envios,
            'envios_entregados': envios_entregados,
            'envios_transito': envios_transito,
            'reclamos_abiertos': reclamos_abiertos,
            'notif_no_leidas': notif_no_leidas,
            'transportistas_activos': transportistas_activos,
            'ult_envios': ult_envios,
        },
    )

