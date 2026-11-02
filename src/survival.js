/* ---------- Survival: region picker and topic search ---------- */
(() => {
  const { $, store } = window.FK;
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  function setRegion(id) {
    if (!$$('#regionSeg button').some(b => b.dataset.region === id)) id = 'temperate';
    $$('#regionSeg button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.region === id)));
    $$('.region').forEach(r => { r.hidden = r.dataset.region !== id; });
    store.set('region', id);
  }
  $$('#regionSeg button').forEach(b => b.addEventListener('click', () => setRegion(b.dataset.region)));
  setRegion(store.get('region', 'temperate'));

  const topics = $$('#survTopics details.ref');
  $('#survSearch').addEventListener('input', e => {
    const q = e.target.value.trim().toLowerCase();
    $('#survTop').hidden = !!q;
    let any = false;
    topics.forEach(d => {
      const hit = !q || d.textContent.toLowerCase().includes(q);
      d.hidden = !hit; d.open = !!q && hit; any = any || hit;
    });
    $('#survEmpty').hidden = any;
  });
})();

/* ---------- Diagrams: tap to enlarge ---------- */
(() => {
  const { $ } = window.FK;
  const dlg = $('#dlgFig');
  $('#tab-survival').addEventListener('click', e => {
    const b = e.target.closest('.fig button');
    if (!b) return;
    $('#figBody').innerHTML = b.innerHTML;
    const cap = b.parentElement.querySelector('figcaption');
    $('#figCap').textContent = cap ? cap.textContent : '';
    dlg.showModal();
  });
  $('#figClose').addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
})();
