// js base
console.log('static scripts loaded');

(function(){
  var menu = document.getElementById('cc-menu');
  if(!menu) return;
  function applyPadding(){
    try{
      var h = menu.offsetHeight || 0;
      document.body.style.paddingTop = h + 'px';
    }catch(e){}
  }
  var lastY = window.pageYOffset || window.scrollY || 0;
  var ticking = false;
  function onScroll(){
    if(ticking) return; ticking = true;
    window.requestAnimationFrame(function(){
      var y = window.pageYOffset || window.scrollY || 0;
      if(y > 8){ menu.classList.add('cc-menu--shrink'); } else { menu.classList.remove('cc-menu--shrink'); }
      if(y > lastY && y > 50){ menu.classList.add('cc-hide'); } else { menu.classList.remove('cc-hide'); }
      lastY = y;
      applyPadding();
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, {passive:true});
  window.addEventListener('resize', applyPadding);
  document.addEventListener('DOMContentLoaded', applyPadding);
  applyPadding();
  // Mobile nav toggle
  var toggleBtn = document.getElementById('cc-menu-toggle');
  var nav = document.getElementById('cc-nav');
  if(toggleBtn && nav){
    toggleBtn.addEventListener('click', function(){
      var open = nav.classList.toggle('cc-open');
      this.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
})();
