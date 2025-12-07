document.addEventListener('DOMContentLoaded',function(){
  var mapEl = document.getElementById('map-seguimiento');
  var points = [];
  if(mapEl){
    var dataStr = mapEl.getAttribute('data-events') || '[]';
    try{ points = JSON.parse(dataStr); }catch(e){ points=[]; }
    var Lexists = typeof L !== 'undefined';
    if(!Lexists){
      var s = document.createElement('script');
      s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      s.onload = function(){ initMap(points); };
      document.body.appendChild(s);
    }else{
      initMap(points);
    }
  }

  function setDefaultIcons(){
    if(typeof L === 'undefined') return;
    L.Icon.Default.mergeOptions({
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
    });
  }

  var map, userMarker, accuracyCircle;
  function initMap(points){
    if(!mapEl) return;
    setDefaultIcons();
    map = L.map('map-seguimiento', {zoomControl:true});
    var bounds = [];
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18, attribution: '&copy; OpenStreetMap'}).addTo(map);
    (points||[]).forEach(function(p){
      var m = L.marker([p.lat, p.lng]).addTo(map);
      if(p.label){ m.bindPopup(p.label); }
      bounds.push([p.lat, p.lng]);
    });
    if(bounds.length){ map.fitBounds(bounds, {padding:[40,40]}); }
    else { map.setView([-33.45,-70.6667], 12); }
    function refresh(){ try{ map.invalidateSize(true); }catch(e){} }
    setTimeout(refresh, 200);
    window.addEventListener('resize', refresh);
  }

  var btnGeo = document.getElementById('btn-geo');
  var watchId = null;
  function updatePosition(pos){
    var lat = pos.coords.latitude;
    var lng = pos.coords.longitude;
    var acc = pos.coords.accuracy;
    var latEl = document.getElementById('event-lat');
    var lngEl = document.getElementById('event-lng');
    if(latEl && lngEl){ latEl.value = lat; lngEl.value = lng; }
    if(map){
      var ll = [lat, lng];
      if(!userMarker){ userMarker = L.marker(ll).addTo(map); }
      else { userMarker.setLatLng(ll); }
      if(accuracyCircle){ accuracyCircle.setLatLng(ll).setRadius(acc||20); }
      else { accuracyCircle = L.circle(ll, {radius: acc||20, color:'#0d6efd', weight:1, fillOpacity:0.1}).addTo(map); }
      map.setView(ll, Math.max(map.getZoom(), 14));
    }
    var ubicacionEl = document.querySelector('input[name="ubicacion"]');
    if(ubicacionEl){
      fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat='+encodeURIComponent(lat)+'&lon='+encodeURIComponent(lng),{
        headers:{'Accept':'application/json'}
      }).then(function(r){return r.json()}).then(function(data){
        if(data && data.display_name){ ubicacionEl.value = data.display_name; }
      }).catch(function(){});
    }
  }
  if(btnGeo){
    btnGeo.addEventListener('click', function(){
      if(!navigator.geolocation){ return; }
      if(watchId !== null){
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
        btnGeo.classList.remove('btn-success');
        btnGeo.classList.add('btn-light');
        btnGeo.textContent = 'Ubicación actual';
        return;
      }
      var opts = { enableHighAccuracy: true, maximumAge: 0 };
      watchId = navigator.geolocation.watchPosition(function(pos){
        updatePosition(pos);
        btnGeo.classList.remove('btn-light');
        btnGeo.classList.add('btn-success');
        btnGeo.textContent = 'Grabando ubicación…';
      }, function(){
        btnGeo.classList.remove('btn-light');
        btnGeo.classList.add('btn-warning');
        btnGeo.textContent = 'No disponible';
      }, opts);
    });
  }
})
