import json
from urllib import request

def sync_estado_a_plataforma(pedido, estado, tracking_codigo=None, override_url=None):
    plataforma = pedido.plataforma
    url = (override_url or (plataforma.store_url.rstrip('/') + '/api/correos/status'))
    data = {
        'order_id': pedido.pedido_id_externo,
        'order_number': pedido.numero_orden,
        'status': estado,
        'tracking_code': tracking_codigo or (getattr(pedido.envio, 'codigo', None) or ''),
    }
    body = json.dumps(data).encode('utf-8')
    req = request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', 'Bearer ' + (plataforma.api_key or ''))
    try:
        with request.urlopen(req, timeout=5) as resp:
            return resp.status
    except Exception:
        return None
