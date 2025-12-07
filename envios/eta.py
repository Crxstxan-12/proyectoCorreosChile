import math
import json
from urllib import request, parse
from datetime import datetime, timedelta


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))


def geocode_address(addr):
    try:
        url = 'https://nominatim.openstreetmap.org/search?' + parse.urlencode({'q': addr, 'format': 'json', 'limit': 1})
        req = request.Request(url, headers={'User-Agent': 'CorreosChile/ETA'})
        with request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        return None
    return None


def estimate_eta(now, km_remaining, estado):
    base_speed = 30.0  # km/h urbano
    if estado == 'en_transito':
        base_speed = 40.0
    elif estado == 'en_reparto':
        base_speed = 25.0
    hour = now.hour
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        base_speed *= 0.7
    if km_remaining < 2:
        base_speed = max(base_speed * 0.6, 12.0)
    hours = km_remaining / max(base_speed, 10.0)
    return now + timedelta(hours=hours)


def recompute_eta_for_envio(envio, current_lat, current_lng):
    if envio.destino_lat is None or envio.destino_lng is None:
        dest = geocode_address(envio.direccion_destino)
        if dest:
            from django.utils import timezone
            envio.destino_lat = dest[0]
            envio.destino_lng = dest[1]
            envio.save(update_fields=['destino_lat','destino_lng'])
        else:
            return None
    km = haversine_km(float(current_lat), float(current_lng), float(envio.destino_lat), float(envio.destino_lng))
    from django.utils import timezone
    now = timezone.now()
    eta_dt = estimate_eta(now, km, envio.estado)
    envio.fecha_estimada_entrega = eta_dt
    envio.eta_km_restante = round(km, 2)
    envio.eta_actualizado_en = now
    envio.save(update_fields=['fecha_estimada_entrega','eta_km_restante','eta_actualizado_en'])
    return eta_dt, km
