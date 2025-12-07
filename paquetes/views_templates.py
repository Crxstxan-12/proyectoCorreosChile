from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Paquete, HistorialPaquete, RutaPaquete, TipoPaquete, PuntoEntrega
from envios.models import Envio
from seguimiento.models import EventoSeguimiento
from django.db.models import Q, Count, Sum
import json


class DashboardPublicoView(TemplateView):
    """Dashboard público para seguimiento de pedidos sin login"""
    template_name = 'paquetes/dashboard_publico.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener estadísticas generales (sin datos sensibles)
        total_paquetes = Paquete.objects.count()
        paquetes_entregados = Paquete.objects.filter(estado='entregado').count()
        paquetes_en_transito = Paquete.objects.filter(estado__in=['en_transito', 'en_reparto']).count()
        
        # Estadísticas por estado para gráficos
        estados_stats = []
        estados_choices = Paquete._meta.get_field('estado').choices
        for estado, label in estados_choices:
            count = Paquete.objects.filter(estado=estado).count()
            if count > 0:  # Solo mostrar estados que tienen paquetes
                estados_stats.append({
                    'estado': label,
                    'count': count,
                    'porcentaje': round((count / total_paquetes * 100) if total_paquetes > 0 else 0, 1)
                })
        
        # Búsqueda de paquete si se proporciona código
        codigo_buscado = self.request.GET.get('codigo')
        pedido_info = None
        historial_items = None
        
        if codigo_buscado:
            try:
                p = Paquete.objects.select_related('tipo_paquete').get(codigo_seguimiento=codigo_buscado)
                pedido_info = {
                    'codigo': p.codigo_seguimiento,
                    'estado': p.estado,
                    'tipo_servicio': getattr(p.tipo_paquete, 'nombre', ''),
                    'fecha_estimada': getattr(p, 'fecha_estimada_entrega', None),
                    'ultima_actualizacion': getattr(p, 'ultima_actualizacion', None),
                    'fecha_entrega_real': getattr(p, 'fecha_entrega_real', None),
                    'quien_recibe': getattr(p, 'quien_recibe', ''),
                }
                historial_items = [
                    {
                        'estado': h.get_estado_nuevo_display if hasattr(h, 'get_estado_nuevo_display') else h.estado_nuevo,
                        'ubicacion': h.ubicacion,
                        'observacion': h.observacion,
                        'fecha': h.fecha_cambio,
                    }
                    for h in HistorialPaquete.objects.filter(paquete=p).order_by('-fecha_cambio')[:10]
                ]
            except Paquete.DoesNotExist:
                # Fallback: buscar Envío por código
                try:
                    e = Envio.objects.get(codigo=codigo_buscado)
                    last_ev = EventoSeguimiento.objects.filter(envio=e).order_by('-registrado_en').first()
                    ultima = None
                    if last_ev:
                        ultima = last_ev.registrado_en
                    elif getattr(e, 'eta_actualizado_en', None):
                        ultima = e.eta_actualizado_en
                    else:
                        ultima = e.actualizado_en
                    pedido_info = {
                        'codigo': e.codigo,
                        'estado': e.estado,
                        'tipo_servicio': 'Envío',
                        'fecha_estimada': getattr(e, 'fecha_estimada_entrega', None),
                        'ultima_actualizacion': ultima,
                        'fecha_entrega_real': None,
                        'quien_recibe': '',
                    }
                    historial_items = [
                        {
                            'estado': ev.estado,
                            'ubicacion': ev.ubicacion,
                            'observacion': ev.observacion,
                            'fecha': ev.registrado_en,
                        }
                        for ev in EventoSeguimiento.objects.filter(envio=e).order_by('-registrado_en')[:10]
                    ]
                except Envio.DoesNotExist:
                    context['error_busqueda'] = f'No se encontró ningún pedido con el código: {codigo_buscado}'
        
        context.update({
            'total_paquetes': total_paquetes,
            'paquetes_entregados': paquetes_entregados,
            'paquetes_en_transito': paquetes_en_transito,
            'estados_stats': estados_stats,
            'codigo_buscado': codigo_buscado,
            'pedido_info': pedido_info,
            'historial_items': historial_items,
        })
        
        return context


class SeguimientoClienteView(TemplateView):
    template_name = 'paquetes/seguimiento_cliente.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        codigo_tracking = self.request.GET.get('codigo_tracking')
        
        if codigo_tracking:
            try:
                paquete = Paquete.objects.select_related(
                    'remitente', 'destinatario', 'tipo_paquete'
                ).get(codigo_seguimiento=codigo_tracking)
                
                historial = HistorialPaquete.objects.filter(
                    paquete=paquete
                ).order_by('-fecha_cambio')
                
                ruta = RutaPaquete.objects.filter(
                    paquete=paquete
                ).order_by('orden_en_ruta')
                
                # Mapeo de estados para mostrar en español claro
                estados_espanol = {
                    'registrado': 'Registrado',
                    'en_almacen': 'En almacén',
                    'en_transito': 'En tránsito',
                    'en_reparto': 'En reparto',
                    'entregado': 'Entregado',
                    'entrega_fallida': 'Entrega fallida',
                    'devuelto': 'Devuelto al remitente',
                    'perdido': 'Perdido',
                    'danado': 'Dañado'
                }
                
                context.update({
                    'paquete': paquete,
                    'historial': historial,
                    'ruta': ruta,
                    'estado_actual': estados_espanol.get(paquete.estado, paquete.estado),
                    'codigo_tracking': codigo_tracking
                })
                
            except Paquete.DoesNotExist:
                context['error'] = 'No se encontró ningún paquete con ese código de tracking.'
        
        return context


class DashboardPaquetesView(TemplateView):
    template_name = 'paquetes/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas generales
        total_paquetes = Paquete.objects.count()
        
        # Paquetes por estado
        paquetes_por_estado = {}
        for estado, _ in Paquete.ESTADO_PAQUETE:
            count = Paquete.objects.filter(estado=estado).count()
            paquetes_por_estado[estado] = count
        
        # Paquetes recientes (últimos 10)
        paquetes_recientes = Paquete.objects.select_related(
            'remitente', 'destinatario', 'tipo_paquete'
        ).order_by('-fecha_creacion')[:10]
        
        # Paquetes en tránsito o reparto (requieren atención)
        paquetes_activos = Paquete.objects.filter(
            estado__in=['en_transito', 'en_reparto']
        ).select_related('remitente', 'destinatario').order_by('fecha_creacion')
        
        context.update({
            'total_paquetes': total_paquetes,
            'paquetes_por_estado': paquetes_por_estado,
            'paquetes_recientes': paquetes_recientes,
            'paquetes_activos': paquetes_activos,
            'total_activos': paquetes_activos.count()
        })
        
        return context


class BuscarPaqueteView(TemplateView):
    template_name = 'paquetes/buscar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        query = self.request.GET.get('q')
        if query:
            paquetes = Paquete.objects.filter(
                Q(codigo_seguimiento__icontains=query) |
                Q(remitente__nombre_completo__icontains=query) |
                Q(remitente__numero_documento__icontains=query) |
                Q(destinatario__nombre_completo__icontains=query) |
                Q(destinatario__email__icontains=query)
            ).select_related('remitente', 'destinatario', 'tipo_paquete').order_by('-fecha_creacion')
            
            context.update({
                'paquetes': paquetes,
                'query': query,
                'total_resultados': paquetes.count()
            })
        
        return context


class CrearPaqueteView(TemplateView):
    template_name = 'paquetes/crear.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener datos necesarios para el formulario
        tipos_paquete = TipoPaquete.objects.filter(activo=True)
        puntos_entrega = PuntoEntrega.objects.filter(activo=True)
        
        context.update({
            'tipos_paquete': tipos_paquete,
            'puntos_entrega': puntos_entrega
        })
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class APIBusquedaAjaxView(TemplateView):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            query = data.get('query', '')
            
            if len(query) >= 3:  # Mínimo 3 caracteres para búsqueda
                paquetes = Paquete.objects.filter(
                    Q(codigo_seguimiento__icontains=query) |
                    Q(remitente__nombre_completo__icontains=query) |
                    Q(destinatario__nombre_completo__icontains=query)
                ).select_related('remitente', 'destinatario')[:5]
                envios = Envio.objects.filter(
                    Q(codigo__icontains=query) |
                    Q(destinatario_nombre__icontains=query) |
                    Q(origen__icontains=query) |
                    Q(destino__icontains=query)
                )[:5]
                resultados = []
                for paquete in paquetes:
                    resultados.append({
                        'tipo': 'paquete',
                        'id': paquete.id,
                        'codigo': paquete.codigo_seguimiento,
                        'titulo': paquete.codigo_seguimiento,
                        'sub': f"{paquete.remitente.nombre_completo} → {paquete.destinatario.nombre_completo}",
                        'estado': paquete.get_estado_display(),
                    })
                for envio in envios:
                    resultados.append({
                        'tipo': 'envio',
                        'id': envio.id,
                        'codigo': envio.codigo,
                        'titulo': envio.codigo,
                        'sub': f"{getattr(envio,'origen','')} → {getattr(envio,'destino','')}",
                        'estado': envio.estado,
                    })
                
                return JsonResponse({'resultados': resultados})
            else:
                return JsonResponse({'resultados': []})
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos inválidos'}, status=400)


class ReportePaquetesView(TemplateView):
    template_name = 'paquetes/reporte.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtros del reporte
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        estado = self.request.GET.get('estado')
        
        paquetes = Paquete.objects.select_related(
            'remitente', 'destinatario', 'tipo_paquete'
        )
        
        if fecha_inicio:
            paquetes = paquetes.filter(fecha_creacion__gte=fecha_inicio)
        if fecha_fin:
            paquetes = paquetes.filter(fecha_creacion__lte=fecha_fin)
        if estado:
            paquetes = paquetes.filter(estado=estado)
        
        # Resumen por tipo de paquete
        resumen_tipo = paquetes.values('tipo_paquete__nombre').annotate(
            cantidad=Count('id'),
            total_peso=Sum('peso_kg'),
            total_precio=Sum('monto_total')
        ).order_by('-cantidad')
        
        context.update({
            'paquetes': paquetes.order_by('-fecha_creacion'),
            'total_paquetes': paquetes.count(),
            'resumen_tipo': resumen_tipo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'estado': estado
        })
        
        return context
