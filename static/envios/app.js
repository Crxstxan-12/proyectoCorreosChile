document.addEventListener('DOMContentLoaded',function(){
  var form = document.getElementById('scan-form');
  if(!form) return;
  var resultEl = document.getElementById('scan-result');
  form.addEventListener('submit', function(e){
    e.preventDefault();
    var envio = document.getElementById('scan-envio').value.trim();
    var codigosText = document.getElementById('scan-codigos').value.trim();
    var csrftokenInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
    var csrftoken = csrftokenInput ? csrftokenInput.value : '';
    if(!envio || !codigosText){
      resultEl.innerHTML = '<div class="alert alert-warning">Complete envío y códigos.</div>';
      return;
    }
    var latEl = document.getElementById('scan-lat');
    var lngEl = document.getElementById('scan-lng');
    var lat = latEl ? latEl.value : '';
    var lng = lngEl ? lngEl.value : '';
    var ubicacionEl = document.getElementById('scan-ubicacion');
    var ubicacion = ubicacionEl ? ubicacionEl.value : '';
    fetch('/envios/scan/',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRFToken':csrftoken},
      body: JSON.stringify({envio_codigo: envio, codigos_text: codigosText, lat: lat, lng: lng, ubicacion: ubicacion})
    }).then(function(r){return r.json()}).then(function(data){
      if(!data.ok){
        resultEl.innerHTML = '<div class="alert alert-danger">'+(data.error||'Error')+'</div>';
        return;
      }
      resultEl.innerHTML = '<div class="alert alert-success">Envío '+data.envio_codigo+': '+data.marcados_entregados+' entregados, '+data.creados+' creados. Estado: '+data.estado_envio+'</div>';
      document.getElementById('scan-codigos').value='';
    }).catch(function(){
      resultEl.innerHTML = '<div class="alert alert-danger">Error de red</div>';
    });
  });
  var btnGeo = document.getElementById('scan-geo');
  if(btnGeo){
    btnGeo.addEventListener('click', function(){
      if(!navigator.geolocation){return;}
      navigator.geolocation.getCurrentPosition(function(pos){
        var lat = pos.coords.latitude;
        var lng = pos.coords.longitude;
        var latEl = document.getElementById('scan-lat');
        var lngEl = document.getElementById('scan-lng');
        if(latEl && lngEl){ latEl.value = lat; lngEl.value = lng; }
        var ubicacionEl = document.getElementById('scan-ubicacion');
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