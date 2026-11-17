/* ---------- Router: every screen has an address, so the Back button works ---------- */
(() => {
  const FK = window.FK;
  const TABS = ['survival', 'tactical', 'emergency'];
  const storedTab = () => { const t = FK.store.get('tab', 'tactical'); return TABS.includes(t) ? t : 'tactical'; };
  const hashOf = r => '#/' + [r.tab, ...r.parts].join('/');
  let route = null;

  /* '#/<tab>/<part>/<part>' -> { tab, parts }. An empty or unknown tab means the stored tab. */
  function parse(hash) {
    const segs = String(hash || '').replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
    return TABS.includes(segs[0]) ? { tab: segs[0], parts: segs.slice(1) } : { tab: storedTab(), parts: [] };
  }

  function apply(r) {
    if (r.tab === 'tactical') {
      const v = ['map', 'position', 'ballistics'].includes(r.parts[0]) ? r.parts[0] : FK.view();
      r = { tab: 'tactical', parts: [v, ...r.parts.slice(1)] };
    }
    FK.showTab(r.tab);
    if (r.tab === 'tactical') FK.showView(r.parts[0]);
    route = r;
    FK.emit('route', r);
    return r;
  }

  /* Browser-driven change (Back/Forward, edited address). Fix up a bad address without a new entry. */
  function onNavigate() {
    if (route && location.hash === hashOf(route)) return;
    const r = apply(parse(location.hash));
    if (location.hash !== hashOf(r)) history.replaceState(null, '', hashOf(r));
  }

  function go(path, opts) {
    const r = parse('#' + path);
    const full = r.tab === 'tactical' && !r.parts.length ? { tab: 'tactical', parts: [FK.view()] } : r;
    if (location.hash === hashOf(full) && route) return;
    history[opts && opts.replace ? 'replaceState' : 'pushState'](null, '', hashOf(full));
    apply(full);
  }

  FK.route = { parse, go, current: () => route || parse(location.hash) };
  addEventListener('popstate', onNavigate);
  addEventListener('hashchange', onNavigate);
  // First route replaces the entry, so opening the app adds no history.
  const first = apply(parse(location.hash));
  history.replaceState(null, '', hashOf(first));
})();
