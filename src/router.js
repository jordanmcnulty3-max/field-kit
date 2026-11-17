/* ---------- Router: every screen has an address, so the Back button works ---------- */
(() => {
  const FK = window.FK;
  const TABS = ['survival', 'tactical', 'emergency'];
  const storedTab = () => { const t = FK.store.get('tab', 'tactical'); return TABS.includes(t) ? t : 'tactical'; };
  const hashOf = r => '#/' + [r.tab, ...r.parts].join('/');
  let route = null;
  let searching = false;   // '#/search' is an overlay on top of whatever tab or screen is underneath; `route` stays that underlying screen
  const isSearchHash = h => /^#\/search\/?$/.test(String(h || ''));

  const safeDecode = x => { try { return decodeURIComponent(x); } catch { return x; } };

  /* '#/<tab>/<part>/<part>' -> { tab, parts }. An empty or unknown tab means the stored tab.
     '#/search' is not a tab: it parses to the tab underneath plus search:true. */
  function parse(hash) {
    if (isSearchHash(hash)) return { tab: route ? route.tab : storedTab(), parts: route ? route.parts.slice() : [], search: true };
    const segs = String(hash || '').replace(/^#\/?/, '').split('/').filter(Boolean).map(safeDecode);
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

  function setSearching(on) {
    if (searching === on) return;
    searching = on;
    FK.emit('search', { open: on });
  }

  /* Browser-driven change (Back/Forward, edited address). Fix up a bad address without a new entry. */
  function onNavigate() {
    if (isSearchHash(location.hash)) { if (route) setSearching(true); return; }
    setSearching(false);
    if (route && location.hash === hashOf(route)) return;
    const r = apply(parse(location.hash));
    if (location.hash !== hashOf(r)) history.replaceState(null, '', hashOf(r));
  }

  function go(path, opts) {
    if (isSearchHash('#' + path)) {
      if (!searching) { history.pushState(null, '', '#/search'); setSearching(true); }
      return;
    }
    setSearching(false);   // any other destination closes the search overlay first
    const r = parse('#' + path);
    const full = r.tab === 'tactical' && !r.parts.length ? { tab: 'tactical', parts: [FK.view()] } : r;
    if (location.hash === hashOf(full) && route) return;
    history[opts && opts.replace ? 'replaceState' : 'pushState'](null, '', hashOf(full));
    apply(full);
  }

  FK.route = { parse, go, current: () => route || parse(location.hash), isSearch: () => searching,
    /* Close the overlay by replacing '#/search' with the underlying screen's address. The screen underneath is already showing, so nothing is re-applied. */
    closeSearch() { if (searching && route) { history.replaceState(history.state, '', hashOf(route)); setSearching(false); } } };
  addEventListener('popstate', onNavigate);
  addEventListener('hashchange', onNavigate);
  // First route replaces the entry, so opening the app adds no history. A reload on '#/search' lands on the tab underneath.
  const first = apply(isSearchHash(location.hash) ? { tab: storedTab(), parts: [] } : parse(location.hash));
  history.replaceState(null, '', hashOf(first));
})();
