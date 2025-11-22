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
from django.db.models import Q
from django.utils import timezone
from .models import PlataformaEcommerce, PedidoEcommerce, ProductoPedido, WebhookLog
from envios.models import Envio, Bulto
from seguimiento.models import EventoSeguimiento
from notificaciones.models import Notificacion
from usuarios.models import Perfil


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
    
    ctx = {
        'plataformas': plataformas,
        'tipos_disponibles': PlataformaEcommerce.PLATAFORMAS,
    }
    
    return render(request, 'ecommerce/configurar.html', ctx)