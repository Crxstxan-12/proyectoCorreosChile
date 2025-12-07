import json
import hmac
import hashlib
import base64
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from .models import PlataformaEcommerce, PedidoEcommerce, ProductoPedido, WebhookLog
from envios.models import Envio, Bulto
from transportista.models import Transportista
from seguimiento.models import EventoSeguimiento
from notificaciones.models import Notificacion
from usuarios.models import Perfil
from .services import sync_estado_a_plataforma
from django.conf import settings
import os
import json as _json


@csrf_exempt
@require_POST
def shopify_webhook(request, plataforma_id):
    """
    Webhook para recibir eventos de Shopify
    """
    try:
        plataforma = PlataformaEcommerce.objects.get(
            id=plataforma_id, 
            tipo='shopify', 
            esta_activa=True
        )
        
        # Verificar firma del webhook
        shopify_hmac = request.headers.get('X-Shopify-Hmac-Sha256')
        if not shopify_hmac:
            return JsonResponse({'error': 'Falta firma HMAC'}, status=401)
        
        # Verificar HMAC solo si hay webhook_secret configurado
        if not plataforma.webhook_secret:
            WebhookLog.objects.create(
                plataforma=plataforma,
                evento_tipo='webhook_sin_secreto',
                nivel='advertencia',
                mensaje='Webhook recibido sin webhook_secret configurado',
                ip_origen=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                procesado_exitoso=False
            )
            return JsonResponse({'error': 'Webhook secret no configurado'}, status=401)
        
        secret = plataforma.webhook_secret.encode('utf-8')
        body = request.body
        hash_hmac = hmac.new(secret, body, hashlib.sha256).digest()
        computed_hmac = base64.b64encode(hash_hmac).decode('utf-8')
        
        if not hmac.compare_digest(shopify_hmac, computed_hmac):
            WebhookLog.objects.create(
                plataforma=plataforma,
                evento_tipo='webhook_invalido',
                nivel='error',
                mensaje='Firma HMAC inválida',
                ip_origen=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                procesado_exitoso=False
            )
            return JsonResponse({'error': 'Firma inválida'}, status=401)
        
        # Procesar el webhook
        data = json.loads(body)
        event_type = request.headers.get('X-Shopify-Topic', 'unknown')
        
        # Log del webhook
        webhook_log = WebhookLog.objects.create(
            plataforma=plataforma,
            evento_tipo=event_type,
            evento_id=data.get('id'),
            nivel='info',
            mensaje=f'Webhook recibido: {event_type}',
            datos_recibidos=data,
            ip_origen=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            procesado_exitoso=True
        )
        
        # Procesar según el tipo de evento
        if event_type == 'orders/create':
            procesar_pedido_shopify(plataforma, data, webhook_log)
        elif event_type == 'orders/updated':
            actualizar_pedido_shopify(plataforma, data, webhook_log)
        elif event_type == 'orders/cancelled':
            cancelar_pedido_shopify(plataforma, data, webhook_log)
        
        return JsonResponse({'status': 'ok'})
        
    except PlataformaEcommerce.DoesNotExist:
        return JsonResponse({'error': 'Plataforma no encontrada'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR EN WEBHOOK: {error_details}")  # Log detallado en consola
        WebhookLog.objects.create(
            plataforma=plataforma if 'plataforma' in locals() else None,
            evento_tipo='error_general',
            nivel='error',
            mensaje=f'Error procesando webhook: {str(e)} - {error_details}',
            datos_recibidos=data if 'data' in locals() else None,
            ip_origen=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            procesado_exitoso=False
        )
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)


def procesar_pedido_shopify(plataforma, data, webhook_log):
    """
    Procesar un nuevo pedido de Shopify
    """
    try:
        # Verificar si el pedido ya existe
        pedido_existente = PedidoEcommerce.objects.filter(
            plataforma=plataforma,
            pedido_id_externo=str(data['id'])
        ).first()
        
        if pedido_existente:
            webhook_log.mensaje += " - Pedido ya existente"
            webhook_log.save()
            return
        
        # Crear el pedido
        pedido = PedidoEcommerce.objects.create(
            plataforma=plataforma,
            pedido_id_externo=str(data['id']),
            numero_orden=data['name'],
            cliente_nombre=f"{data['customer']['first_name']} {data['customer']['last_name']}",
            cliente_email=data['customer']['email'],
            cliente_telefono=data.get('phone', ''),
            direccion_entrega=_obtener_direccion_shopify(data.get('shipping_address', {})),
            direccion_envio=_obtener_direccion_shopify(data.get('billing_address', {})),
            total=float(data['total_price']),
            moneda=data['currency'],
            estado='pendiente',
            fecha_pedido=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            datos_raw=data
        )
        
        # Crear productos del pedido
        for item in data.get('line_items', []):
            ProductoPedido.objects.create(
                pedido=pedido,
                sku=item['sku'] or item['variant_id'],
                nombre=item['name'],
                cantidad=item['quantity'],
                precio_unitario=float(item['price']),
                peso_kg=float(item.get('grams', 0)) / 1000 if item.get('grams') else None,
                dimensiones=item.get('variant_title', '')
            )
        
        # Crear envío asociado
        envio = _crear_envio_desde_pedido(pedido)
        pedido.envio = envio
        pedido.save()
        
        # Notificar al administrador
        _notificar_nuevo_pedido(pedido)
        
        webhook_log.mensaje += f" - Pedido {pedido.numero_orden} creado exitosamente"
        webhook_log.datos_procesados = {'pedido_id': pedido.id, 'envio_id': envio.id}
        webhook_log.save()
        
    except Exception as e:
        webhook_log.nivel = 'error'
        webhook_log.mensaje += f" - Error procesando pedido: {str(e)}"
        webhook_log.save()
        raise


def actualizar_pedido_shopify(plataforma, data, webhook_log):
    """
    Actualizar un pedido existente de Shopify
    """
    try:
        pedido = PedidoEcommerce.objects.filter(
            plataforma=plataforma,
            pedido_id_externo=str(data['id'])
        ).first()
        
        if not pedido:
            webhook_log.mensaje += " - Pedido no encontrado para actualizar"
            webhook_log.save()
            return
        
        # Actualizar estado según fulfillment status
        if data.get('fulfillment_status') == 'fulfilled':
            pedido.estado = 'enviado'
            if not pedido.fecha_envio:
                pedido.fecha_envio = timezone.now()
        elif data.get('cancelled_at'):
            pedido.estado = 'cancelado'
        
        pedido.save()
        
        # Actualizar envío asociado si existe
        if pedido.envio:
            if pedido.estado == 'enviado' and pedido.envio.estado != 'en_transito':
                pedido.envio.estado = 'en_transito'
                pedido.envio.save()
                
                # Crear evento de seguimiento
                EventoSeguimiento.objects.create(
                    envio=pedido.envio,
                    estado='en_transito',
                    ubicacion='Despachado desde plataforma e-commerce',
                    observacion=f'Pedido {pedido.numero_orden} despachado desde {plataforma.nombre}'
                )
        
        webhook_log.mensaje += f" - Pedido {pedido.numero_orden} actualizado"
        webhook_log.save()
        
    except Exception as e:
        webhook_log.nivel = 'error'
        webhook_log.mensaje += f" - Error actualizando pedido: {str(e)}"
        webhook_log.save()
        raise


def cancelar_pedido_shopify(plataforma, data, webhook_log):
    """
    Cancelar un pedido de Shopify
    """
    try:
        pedido = PedidoEcommerce.objects.filter(
            plataforma=plataforma,
            pedido_id_externo=str(data['id'])
        ).first()
        
        if not pedido:
            webhook_log.mensaje += " - Pedido no encontrado para cancelar"
            webhook_log.save()
            return
        
        pedido.estado = 'cancelado'
        pedido.save()
        
        # Cancelar envío asociado si existe
        if pedido.envio and pedido.envio.estado != 'cancelado':
            pedido.envio.estado = 'cancelado'
            pedido.envio.save()
        
        webhook_log.mensaje += f" - Pedido {pedido.numero_orden} cancelado"
        webhook_log.save()
        
    except Exception as e:
        webhook_log.nivel = 'error'
        webhook_log.mensaje += f" - Error cancelando pedido: {str(e)}"
        webhook_log.save()
        raise


def _obtener_direccion_shopify(direccion_data):
    """
    Formatear dirección de Shopify
    """
    if not direccion_data:
        return ''
    
    partes = [
        direccion_data.get('address1', ''),
        direccion_data.get('address2', ''),
        direccion_data.get('city', ''),
        direccion_data.get('province', ''),
        direccion_data.get('zip', ''),
        direccion_data.get('country', '')
    ]
    
    return ', '.join([p for p in partes if p.strip()])


def _crear_envio_desde_pedido(pedido):
    """
    Crear un envío en el sistema a partir de un pedido e-commerce
    """
    # Generar código único para el envío
    codigo_envio = f"EC-{pedido.plataforma.tipo.upper()}-{pedido.numero_orden}"
    
    # Calcular peso total
    peso_total = sum(
        (p.peso_kg or 0.5) * p.cantidad  # 0.5kg por defecto si no hay peso
        for p in pedido.productos.all()
    )
    
    # Crear envío
    envio = Envio.objects.create(
        codigo=codigo_envio,
        estado='pendiente',
        origen='Depósito Central CorreosChile',
        destino=pedido.direccion_entrega[:100],  # Limitar a 100 caracteres
        destinatario_nombre=pedido.cliente_nombre,
        direccion_destino=pedido.direccion_entrega,
        peso_kg=peso_total or 1.0,  # 1kg mínimo
        costo=pedido.total,
        usuario=pedido.plataforma.usuario if pedido.plataforma.usuario else None
    )
    
    # Crear bultos para cada producto
    for producto in pedido.productos.all():
        for i in range(producto.cantidad):
            Bulto.objects.create(
                envio=envio,
                codigo_barras=f"{codigo_envio}-{producto.sku}-{i+1}",
                peso_kg=producto.peso_kg or 0.5
            )
    
    return envio


def _notificar_nuevo_pedido(pedido):
    """
    Notificar sobre nuevo pedido e-commerce
    """
    Notificacion.objects.create(
        titulo=f"Nuevo pedido de {pedido.plataforma.nombre}",
        mensaje=f"Pedido {pedido.numero_orden} de {pedido.cliente_nombre} - Total: ${pedido.total}",
        tipo='info',
        canal='web',
        usuario=pedido.plataforma.usuario
    )


@login_required
def index(request):
    """
    Vista principal de administración de e-commerce
    """
    q = request.GET.get('q', '').strip()
    plataforma_id = request.GET.get('plataforma', '').strip()
    estado = request.GET.get('estado', '').strip()
    
    queryset = PedidoEcommerce.objects.select_related('plataforma', 'envio')
    
    if q:
        queryset = queryset.filter(
            Q(numero_orden__icontains=q) |
            Q(cliente_nombre__icontains=q) |
            Q(cliente_email__icontains=q)
        )
    
    if plataforma_id:
        queryset = queryset.filter(plataforma_id=plataforma_id)
    
    if estado:
        queryset = queryset.filter(estado=estado)
    
    queryset = queryset.order_by('-creado_en')
    
    # Estadísticas
    total_pedidos = PedidoEcommerce.objects.count()
    pedidos_pendientes = PedidoEcommerce.objects.filter(estado='pendiente').count()
    pedidos_procesados = PedidoEcommerce.objects.filter(estado='procesado').count()
    pedidos_enviados = PedidoEcommerce.objects.filter(estado='enviado').count()
    
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    ctx = {
        'pedidos': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'plataforma_seleccionada': plataforma_id,
        'estado_seleccionado': estado,
        'plataformas': PlataformaEcommerce.objects.filter(esta_activa=True),
        'estados': [e[0] for e in PedidoEcommerce.ESTADOS_PEDIDO],
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_procesados': pedidos_procesados,
        'pedidos_enviados': pedidos_enviados,
        'transportistas': Transportista.objects.filter(activo=True).order_by('nombre'),
    }
    
    return render(request, 'ecommerce/index.html', ctx)


@login_required
def configurar_plataforma(request):
    """
    Vista para configurar plataformas e-commerce
    """
    # Verificar permisos
    if not Perfil.objects.filter(user=request.user, rol__in=['administrador', 'editor']).exists():
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            plataforma_id = data.get('id')
            if plataforma_id:
                # Actualizar existente
                plataforma = get_object_or_404(PlataformaEcommerce, id=plataforma_id, usuario=request.user)
            else:
                # Crear nueva
                plataforma = PlataformaEcommerce(usuario=request.user)
            
            plataforma.nombre = data['nombre']
            plataforma.tipo = data['tipo']
            plataforma.api_key = data['api_key']
            plataforma.api_secret = data.get('api_secret', '')
            plataforma.webhook_secret = data.get('webhook_secret', '')
            plataforma.store_url = data['store_url']
            plataforma.esta_activa = data.get('esta_activa', True)
            plataforma.save()
            
            return JsonResponse({
                'status': 'ok',
                'plataforma': {
                    'id': plataforma.id,
                    'nombre': plataforma.nombre,
                    'tipo': plataforma.tipo,
                    'store_url': plataforma.store_url,
                    'esta_activa': plataforma.esta_activa
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # GET - Obtener plataformas del usuario
    plataformas = PlataformaEcommerce.objects.filter(usuario=request.user)
    resumen_estados = (
        PedidoEcommerce.objects.filter(plataforma__usuario=request.user)
        .values('estado')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )
    logs_webhook = (
        WebhookLog.objects.filter(plataforma__usuario=request.user)
        .select_related('plataforma')
        .order_by('-creado_en')[:20]
    )
    
    ctx = {
        'plataformas': plataformas,
        'tipos_disponibles': PlataformaEcommerce.PLATAFORMAS,
        'resumen_estados': resumen_estados,
        'logs_webhook': logs_webhook,
    }
    
    return render(request, 'ecommerce/configurar.html', ctx)


@login_required
def procesar_pedido(request, pedido_id):
    """Marca un pedido como procesado y actualiza su envío asociado"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        permitido = Perfil.objects.filter(user=request.user, rol__in=['administrador', 'editor']).exists()
        if not permitido:
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        pedido = PedidoEcommerce.objects.get(id=pedido_id)
        pedido.estado = 'procesado'
        pedido.save(update_fields=['estado', 'actualizado_en'])
        if pedido.envio and pedido.envio.estado == 'pendiente':
            pedido.envio.estado = 'en_transito'
            pedido.envio.save(update_fields=['estado', 'actualizado_en'])
            EventoSeguimiento.objects.create(
                envio=pedido.envio,
                estado='en_transito',
                ubicacion='Procesado desde panel e-commerce',
                observacion=f'Pedido {pedido.numero_orden} procesado'
            )
        return JsonResponse({'status': 'ok'})
    except PedidoEcommerce.DoesNotExist:
        return JsonResponse({'error': 'Pedido no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def asignar_transportista(request, pedido_id):
    """Asigna un transportista al envío asociado de un pedido e-commerce"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        permitido_admin = Perfil.objects.filter(user=request.user, rol__in=['administrador', 'editor']).exists()
        # Dueño del pedido (plataforma asociada al usuario)
        permitido_duenio = False
        try:
            ped_check = PedidoEcommerce.objects.get(id=pedido_id)
            permitido_duenio = (ped_check.plataforma.usuario == request.user)
        except PedidoEcommerce.DoesNotExist:
            permitido_duenio = False
        if not (permitido_admin or permitido_duenio):
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        pedido = PedidoEcommerce.objects.get(id=pedido_id)
        if not pedido.envio:
            return JsonResponse({'error': 'Pedido sin envío asociado'}, status=400)
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        tid = int(data.get('transportista_id'))
        t = Transportista.objects.get(id=tid, activo=True)
        pedido.envio.transportista = t
        pedido.envio.save(update_fields=['transportista', 'actualizado_en'])
        return JsonResponse({'status': 'ok'})
    except PedidoEcommerce.DoesNotExist:
        return JsonResponse({'error': 'Pedido no encontrado'}, status=404)
    except Transportista.DoesNotExist:
        return JsonResponse({'error': 'Transportista no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def nuevo_pedido(request):
    """Formulario para que el usuario cree un pedido manual y lo visualice luego"""
    created = False
    pedido = None
    if request.method == 'POST':
        try:
            data = request.POST
            # Obtener/crear plataforma personalizada para el usuario
            plataforma, _ = PlataformaEcommerce.objects.get_or_create(
                usuario=request.user,
                nombre='Pedidos Directos',
                defaults={'tipo':'custom','api_key':'-', 'store_url':'http://localhost', 'esta_activa':True}
            )
            numero_orden = (data.get('numero_orden') or f"USR-{request.user.id}-{int(timezone.now().timestamp())}")
            pedido = PedidoEcommerce.objects.create(
                plataforma=plataforma,
                pedido_id_externo=numero_orden,
                numero_orden=numero_orden,
                cliente_nombre=data.get('cliente_nombre',''),
                cliente_email=data.get('cliente_email',''),
                cliente_telefono=data.get('cliente_telefono',''),
                direccion_entrega=data.get('direccion_entrega',''),
                total=float(data.get('total') or 0),
                moneda=(data.get('moneda') or 'CLP')[:3],
                estado='pendiente',
                fecha_pedido=timezone.now(),
            )
            # Parseo simple de items: sku,nombre,cantidad,precio por línea
            items_text = data.get('items_text','').strip()
            for line in [l for l in items_text.replace('\r','\n').split('\n') if l.strip()]:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 4:
                    ProductoPedido.objects.create(
                        pedido=pedido,
                        sku=parts[0], nombre=parts[1], cantidad=int(parts[2]), precio_unitario=float(parts[3])
                    )
            envio = _crear_envio_desde_pedido(pedido)
            pedido.envio = envio
            pedido.save()
            created = True
        except Exception:
            created = False
    return render(request, 'ecommerce/nuevo_pedido.html', {'created': created, 'pedido': pedido})


@login_required
def mis_pedidos(request):
    """Listado de pedidos creados por el usuario (plataformas del usuario)"""
    queryset = PedidoEcommerce.objects.select_related('plataforma','envio').filter(plataforma__usuario=request.user).order_by('-creado_en')
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'ecommerce/mis_pedidos.html', {
        'pedidos': page_obj.object_list,
        'page_obj': page_obj,
        'transportistas': Transportista.objects.filter(activo=True).order_by('nombre')
    })

@login_required
def tienda(request):
    """Tienda simple para que el usuario cree pedidos en dos empresas: Shopify y Amazon"""
    def _cargar_catalogo():
        try:
            path = os.path.join(settings.BASE_DIR, 'static', 'ecommerce', 'catalogo.json')
            with open(path, 'r', encoding='utf-8') as f:
                data = _json.load(f)
                return data
        except Exception:
            return None

    productos = _cargar_catalogo() or {
        'shopify': [
            {'sku':'SH-1001','nombre':'Polera Correos', 'precio': 12990, 'img': '/static/img/tienda/polera_correos.svg', 'peso':0.3, 'orden':1},
            {'sku':'SH-1002','nombre':'Gorro Azul', 'precio': 7990, 'img': '/static/img/tienda/gorro_azul.svg', 'peso':0.2, 'orden':2},
            {'sku':'SH-1003','nombre':'Polerón Rojo', 'precio': 19990, 'img': '/static/img/tienda/poleron_rojo.svg', 'peso':0.6, 'orden':3},
        ],
        'amazon': [
            {'sku':'AM-2001','nombre':'Caja pequeña', 'precio': 3990, 'img': '/static/img/tienda/caja_pequena.svg', 'peso':0.4, 'orden':1},
            {'sku':'AM-2002','nombre':'Caja mediana', 'precio': 6990, 'img': '/static/img/tienda/caja_mediana.svg', 'peso':0.8, 'orden':2},
            {'sku':'AM-2003','nombre':'Caja grande', 'precio': 9990, 'img': '/static/img/tienda/caja_grande.svg', 'peso':1.5, 'orden':3},
        ]
    }
    # Ordenar por 'orden' si existe
    for k in list(productos.keys()):
        try:
            productos[k] = sorted(productos[k], key=lambda x: x.get('orden', 999))
        except Exception:
            pass
    created = False
    pedido = None
    error = ''
    if request.method == 'POST':
        try:
            empresa = (request.POST.get('empresa') or 'shopify').strip()
            if empresa not in ['shopify','amazon']:
                empresa = 'shopify'
            nombre = (request.POST.get('cliente_nombre') or '').strip()
            email = (request.POST.get('cliente_email') or '').strip()
            telefono = (request.POST.get('cliente_telefono') or '').strip()
            direccion = (request.POST.get('direccion_entrega') or '').strip()
            items_text = (request.POST.get('items_text') or '').strip()
            if not nombre or not email or not direccion:
                raise ValueError('Faltan datos del cliente')
            plataforma, _ = PlataformaEcommerce.objects.get_or_create(
                usuario=request.user,
                nombre=f'Tienda {empresa.title()}',
                defaults={'tipo':empresa, 'api_key':'-', 'store_url':'http://localhost', 'esta_activa':True}
            )
            numero_orden = f"WEB-{empresa.upper()}-{int(timezone.now().timestamp())}"
            pedido = PedidoEcommerce.objects.create(
                plataforma=plataforma,
                pedido_id_externo=numero_orden,
                numero_orden=numero_orden,
                cliente_nombre=nombre,
                cliente_email=email,
                cliente_telefono=telefono,
                direccion_entrega=direccion,
                total=float(request.POST.get('total') or 0),
                moneda='CLP',
                estado='pendiente',
                fecha_pedido=timezone.now(),
            )
            for line in [l for l in items_text.replace('\r','\n').split('\n') if l.strip()]:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 4:
                    ProductoPedido.objects.create(
                        pedido=pedido,
                        sku=parts[0], nombre=parts[1], cantidad=int(parts[2]), precio_unitario=float(parts[3])
                    )
            envio = _crear_envio_desde_pedido(pedido)
            pedido.envio = envio
            pedido.save()
            created = True
        except ValueError as e:
            error = str(e)
        except Exception:
            error = 'Error al crear pedido'
    return render(request, 'ecommerce/tienda.html', {
        'productos': productos,
        'created': created,
        'pedido': pedido,
        'error': error,
    })

@login_required
def reenviar_estado(request, pedido_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        pedido = PedidoEcommerce.objects.select_related('envio','plataforma').get(id=pedido_id)
        envio = pedido.envio
        if not envio:
            return JsonResponse({'error': 'Pedido sin envío'}, status=400)
        status_code = sync_estado_a_plataforma(pedido, envio.estado, tracking_codigo=getattr(envio,'codigo',None))
        return JsonResponse({'status': 'ok', 'status_code': status_code})
    except PedidoEcommerce.DoesNotExist:
        return JsonResponse({'error': 'Pedido no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def sandbox_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            data = {'raw': request.body.decode('utf-8','ignore')}
        WebhookLog.objects.create(
            plataforma=PlataformaEcommerce.objects.filter(esta_activa=True).first(),
            evento_tipo='sandbox_status',
            nivel='info',
            mensaje='Sandbox status recibido',
            datos_recibidos=data,
            ip_origen=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            procesado_exitoso=True
        )
        return JsonResponse({'status':'ok'})
    # GET: mostrar últimos
    logs = WebhookLog.objects.filter(evento_tipo='sandbox_status').order_by('-creado_en')[:20]
    return render(request, 'ecommerce/sandbox_status.html', {'logs': logs})

@login_required
def probar_sync(request, pedido_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        pedido = PedidoEcommerce.objects.select_related('envio').get(id=pedido_id)
        envio = pedido.envio
        if not envio:
            return JsonResponse({'error': 'Pedido sin envío'}, status=400)
        override = request.build_absolute_uri('/ecommerce/sandbox/status')
        status_code = sync_estado_a_plataforma(pedido, envio.estado, tracking_codigo=getattr(envio,'codigo',None), override_url=override)
        return JsonResponse({'status':'ok','status_code':status_code})
    except PedidoEcommerce.DoesNotExist:
        return JsonResponse({'error': 'Pedido no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
@csrf_exempt
@require_POST
def amazon_webhook(request, plataforma_id):
    """
    Webhook simplificado para recibir eventos de pedidos de Amazon
    Espera un JSON con claves principales: orderId, orderNumber, buyer, shippingAddress, items, currency, purchaseDate
    """
    try:
        plataforma = PlataformaEcommerce.objects.get(id=plataforma_id, tipo='amazon', esta_activa=True)
        data = json.loads(request.body)
        # Log básico del webhook
        WebhookLog.objects.create(
            plataforma=plataforma,
            evento_tipo=data.get('event','orders/create'),
            evento_id=str(data.get('orderId')),
            nivel='info',
            mensaje='Webhook Amazon recibido',
            datos_recibidos=data,
            ip_origen=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            procesado_exitoso=True
        )
        # Procesar pedido
        procesar_pedido_amazon(plataforma, data)
        return JsonResponse({'status': 'ok'})
    except PlataformaEcommerce.DoesNotExist:
        return JsonResponse({'error': 'Plataforma Amazon no encontrada'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)


def procesar_pedido_amazon(plataforma, data):
    """Crea/actualiza un pedido proveniente de Amazon y su envío asociado"""
    # Id y número
    order_id = str(data.get('orderId') or data.get('id') or '')
    numero_orden = data.get('orderNumber') or order_id or f"AMZ-{int(timezone.now().timestamp())}"
    if not order_id:
        order_id = numero_orden
    pedido = PedidoEcommerce.objects.filter(plataforma=plataforma, pedido_id_externo=order_id).first()
    if pedido:
        # Actualización simple de estado
        estado_ext = (data.get('status') or '').lower()
        if estado_ext in ['shipped','enviado']:
            pedido.estado = 'enviado'
            pedido.fecha_envio = timezone.now()
        elif estado_ext in ['cancelled','cancelado']:
            pedido.estado = 'cancelado'
        pedido.save()
        return pedido
    # Crear pedido nuevo
    buyer = data.get('buyer', {})
    shipping = data.get('shippingAddress', {})
    total = float(data.get('total', 0))
    currency = (data.get('currency') or 'CLP')[:3]
    fecha_pedido = data.get('purchaseDate') or timezone.now().isoformat()
    pedido = PedidoEcommerce.objects.create(
        plataforma=plataforma,
        pedido_id_externo=order_id,
        numero_orden=numero_orden,
        cliente_nombre=f"{buyer.get('name') or buyer.get('firstName','')} {buyer.get('lastName','')}".strip() or (buyer.get('name') or 'Amazon Cliente'),
        cliente_email=buyer.get('email','no-reply@example.com'),
        cliente_telefono=buyer.get('phone',''),
        direccion_entrega=_formatear_direccion_amazon(shipping),
        direccion_envio=_formatear_direccion_amazon(data.get('billingAddress', {})),
        total=total,
        moneda=currency,
        estado='pendiente',
        fecha_pedido=datetime.fromisoformat(str(fecha_pedido).replace('Z','+00:00')) if isinstance(fecha_pedido, str) else timezone.now(),
        datos_raw=data
    )
    # Productos
    for item in (data.get('items') or []):
        ProductoPedido.objects.create(
            pedido=pedido,
            sku=str(item.get('sku') or item.get('asin') or ''),
            nombre=item.get('name','Item Amazon'),
            cantidad=int(item.get('quantity') or 1),
            precio_unitario=float(item.get('price') or 0),
            peso_kg=float(item.get('weightKg') or 0) if item.get('weightKg') is not None else None,
            dimensiones=item.get('dimensions','')
        )
    envio = _crear_envio_desde_pedido(pedido)
    pedido.envio = envio
    pedido.save()
    return pedido


def _formatear_direccion_amazon(addr):
    partes = [addr.get('address1',''), addr.get('address2',''), addr.get('city',''), addr.get('state',''), addr.get('postalCode',''), addr.get('country','')]
    return ', '.join([p for p in partes if p])
