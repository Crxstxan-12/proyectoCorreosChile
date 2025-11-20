document.addEventListener('DOMContentLoaded',function(){
  var mapEl = document.getElementById('map-seguimiento');
  if(mapEl){
    var dataStr = mapEl.getAttribute('data-events') || '[]';
    var points = [];
    try{ points = JSON.parse(dataStr); }catch(e){ points=[]; }
    if(points.length){
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
  }

  function initMap(points){
    var map = L.map('map-seguimiento');
    var bounds = [];
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18}).addTo(map);
    points.forEach(function(p){
      var m = L.marker([p.lat, p.lng]).addTo(map);
      if(p.label){ m.bindPopup(p.label); }
      bounds.push([p.lat, p.lng]);
    });
    if(bounds.length){ map.fitBounds(bounds, {padding:[20,20]}); }
    else { map.setView([-33.45,-70.6667], 11); }
  }

  var btnGeo = document.getElementById('btn-geo');
  if(btnGeo){
    btnGeo.addEventListener('click', function(){
      if(!navigator.geolocation){return;}
      navigator.geolocation.getCurrentPosition(function(pos){
        var lat = pos.coords.latitude;
        var lng = pos.coords.longitude;
        var latEl = document.getElementById('event-lat');
        var lngEl = document.getElementById('event-lng');
        if(latEl && lngEl){ latEl.value = lat; lngEl.value = lng; }
        var ubicacionEl = document.querySelector('input[name="ubicacion"]');
        if(ubicacionEl){
          fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat='+encodeURIComponent(lat)+'&lon='+encodeURIComponent(lng),{
            headers:{'Accept':'application/json'}
          }).then(function(r){return r.json()}).then(function(data){
            if(data && data.display_name){ ubicacionEl.value = data.display_name; }
          }).catch(function(){});
        }
        btnGeo.classList.remove('btn-light');
        btnGeo.classList.add('btn-success');
        btnGeo.textContent = 'Ubicación lista';
      }, function(){
        btnGeo.classList.remove('btn-light');
        btnGeo.classList.add('btn-warning');
        btnGeo.textContent = 'No disponible';
      });
    });
  }
})