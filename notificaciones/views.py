from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .models import Notificacion, PreferenciaNotificacion

def index(request):
    saved_pref = False
    pref = None
    if request.user.is_authenticated:
        pref, _ = PreferenciaNotificacion.objects.get_or_create(usuario=request.user)
        if request.method == 'POST' and request.POST.get('action') == 'preferencias':
            pref.canal_web = bool(request.POST.get('canal_web'))
            pref.canal_email = bool(request.POST.get('canal_email'))
            pref.canal_sms = bool(request.POST.get('canal_sms'))
            pref.canal_push = bool(request.POST.get('canal_push'))
            pref.save()
            saved_pref = True
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    canal = request.GET.get('canal', '').strip()
    leida = request.GET.get('leida', '').strip()

    queryset = Notificacion.objects.all()
    if request.user.is_authenticated:
        queryset = queryset.filter(usuario=request.user)
    if q:
        queryset = queryset.filter(Q(titulo__icontains=q) | Q(mensaje__icontains=q))
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if canal:
        queryset = queryset.filter(canal=canal)
    if leida == 'si':
        queryset = queryset.filter(leida=True)
    elif leida == 'no':
        queryset = queryset.filter(leida=False)

    queryset = queryset.order_by('-creado_en')
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    tipos = [t[0] for t in Notificacion.TIPOS]
    canales = [c[0] for c in Notificacion.CANALES]
    counts_tipo = {k: queryset.filter(tipo=k).count() for k in tipos}
    counts_leida = {
        'leidas': queryset.filter(leida=True).count(),
        'no_leidas': queryset.filter(leida=False).count(),
    }

    ctx = {
        'notificaciones': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'tipo': tipo,
        'canal': canal,
        'leida': leida,
        'total_notifs': queryset.count(),
        'notifs_leidas': counts_leida['leidas'],
        'notifs_no_leidas': counts_leida['no_leidas'],
        'count_info': counts_tipo.get('info', 0),
        'count_alerta': counts_tipo.get('alerta', 0),
        'count_error': counts_tipo.get('error', 0),
        'pref': pref,
        'saved_pref': saved_pref,
    }
    return render(request, 'notificaciones/index.html', ctx)
