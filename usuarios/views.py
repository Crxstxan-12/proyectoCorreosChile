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
    MAX_INTENTOS = 3
    login_warning = ''
    blocked_msg = ''
    # Recuperar mensajes tras redirección (PRG)
    ui_state = request.session.pop('login_ui', None)
    if ui_state:
        login_warning = ui_state.get('login_warning', '')
        blocked_msg = ui_state.get('blocked_msg', '')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuario', 'autocomplete': 'username'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña', 'autocomplete': 'current-password'})
        username = request.POST.get('username','').strip()
        from django.contrib.auth.models import User
        perfil = None
        try:
            u = User.objects.filter(username=username).first()
            perfil = Perfil.objects.filter(user=u).first() if u else None
        except Exception:
            perfil = None
        # Bloqueo temporal
        from django.utils import timezone
        session_blocks = request.session.get('login_blocks', {})
        blocked_until = None
        if perfil and perfil.bloqueado_hasta and perfil.bloqueado_hasta > timezone.now():
            blocked_until = perfil.bloqueado_hasta
        elif session_blocks.get(username):
            try:
                blocked_until = timezone.datetime.fromisoformat(session_blocks[username])
            except Exception:
                blocked_until = None
        if blocked_until and blocked_until > timezone.now():
            blocked_msg = 'Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde.'
            request.session['login_ui'] = {'blocked_msg': blocked_msg}
            request.session['login_prefill'] = username
            return redirect('usuarios:login')
        elif form.is_valid():
            user = form.get_user()
            login(request, user)
            if perfil:
                perfil.intentos_fallidos = 0
                perfil.bloqueado_hasta = None
                perfil.save(update_fields=['intentos_fallidos','bloqueado_hasta'])
            attempts = request.session.get('login_attempts', {})
            if username in attempts:
                attempts.pop(username)
                request.session['login_attempts'] = attempts
            blocks = request.session.get('login_blocks', {})
            if username in blocks:
                blocks.pop(username)
                request.session['login_blocks'] = blocks
            return redirect('usuarios:index')
        else:
            # Falló login → incrementar intentos y avisar (sin extender bloqueo al refrescar)
            from datetime import timedelta
            if perfil:
                if not (perfil.bloqueado_hasta and perfil.bloqueado_hasta > timezone.now()):
                    perfil.intentos_fallidos = (perfil.intentos_fallidos or 0) + 1
                restantes = max(0, MAX_INTENTOS - (perfil.intentos_fallidos or 0))
                if restantes > 0:
                    login_warning = f'Te quedan {restantes} intentos antes de bloquear su cuenta'
                else:
                    if not (perfil.bloqueado_hasta and perfil.bloqueado_hasta > timezone.now()):
                        perfil.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
                    blocked_msg = 'Cuenta bloqueada por 15 minutos por intentos fallidos'
                perfil.save(update_fields=['intentos_fallidos','bloqueado_hasta'])
            else:
                attempts = request.session.get('login_attempts', {})
                blocks = request.session.get('login_blocks', {})
                cur = int(attempts.get(username, 0))
                # No incrementar si ya está bloqueado
                blocked = False
                if blocks.get(username):
                    try:
                        bu = timezone.datetime.fromisoformat(blocks[username])
                        blocked = (bu and bu > timezone.now())
                    except Exception:
                        blocked = False
                if not blocked:
                    cur += 1
                attempts[username] = cur
                request.session['login_attempts'] = attempts
                restantes = max(0, MAX_INTENTOS - cur)
                if restantes > 0:
                    login_warning = f'Te quedan {restantes} intentos antes de bloquear su cuenta'
                else:
                    if not blocked:
                        until = (timezone.now() + timedelta(minutes=15)).isoformat()
                        blocks[username] = until
                        request.session['login_blocks'] = blocks
                    blocked_msg = 'Cuenta bloqueada por 15 minutos por intentos fallidos'
            request.session['login_ui'] = {'login_warning': login_warning, 'blocked_msg': blocked_msg}
            request.session['login_prefill'] = username
            return redirect('usuarios:login')
    else:
        form = AuthenticationForm(request)
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuario', 'autocomplete': 'username'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña', 'autocomplete': 'current-password'})
        try:
            pre = request.session.pop('login_prefill')
            form.fields['username'].initial = pre
        except Exception:
            pass
    return render(request, 'usuarios/login.html', {'form': form, 'login_warning': login_warning, 'blocked_msg': blocked_msg})

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

