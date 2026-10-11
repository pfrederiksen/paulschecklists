const filter=document.getElementById('sport-filter');
filter.addEventListener('change',()=>document.querySelectorAll('[data-sport]').forEach(tile=>tile.hidden=Boolean(filter.value&&tile.dataset.sport!==filter.value)));
