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

  /* ---------- History index: every entry the app is on carries its position in history.state[IDX].
     A push is one more than the entry it was pushed from, a replace keeps the number, and a reload keeps
     the entry's state, so the difference between two numbers is always the distance between their entries.
     Fields other modules keep in history.state survive: the router never writes null over them. ---------- */
  const IDX = 'fkIdx';
  let index = 0;
  const stateIndex = () => (history.state && Number.isInteger(history.state[IDX])) ? history.state[IDX] : null;
  const withIndex = (st, i) => ({ ...(st && typeof st === 'object' ? st : {}), [IDX]: i });
  const push = hash => { index += 1; history.pushState(withIndex(null, index), '', hash); };
  /* A replace is a screen change on this entry: a sheet's or a tool mode's marker on it no longer holds, so it is not copied. */
  const replace = hash => {
    const { fkSheet, fkLayer, ...rest } = history.state && typeof history.state === 'object' ? history.state : {};
    history.replaceState(withIndex(rest, index), '', hash);
  };
  /* Back/Forward land on an entry with its number; an edited address or a script-pushed entry has none and
     was added after the entry the app was on. */
  function readIndex() {
    const i = stateIndex();
    if (i === null) { index += 1; history.replaceState(withIndex(history.state, index), '', location.href); }
    else index = i;
  }

  /* Browser-driven change (Back/Forward, edited address). Fix up a bad address without a new entry. */
  let afterPop = [];
  function onNavigate() {
    const was = index;
    readIndex();
    const waiting = afterPop; afterPop = [];
    try {
      if (isSearchHash(location.hash)) { if (route) setSearching(true); return; }
      setSearching(false);
      if (route && location.hash === hashOf(route)) {
        if (index !== was) FK.emit('history', { index });   // same screen, another entry: screens that track entries resync
        return;
      }
      const r = apply(parse(location.hash));
      if (location.hash !== hashOf(r)) replace(hashOf(r));
    } finally { waiting.forEach(fn => { try { fn(); } catch (e) { console.error(e); } }); }
  }

  function go(path, opts) {
    if (isSearchHash('#' + path)) {
      if (!searching) { push('#/search'); setSearching(true); }
      return;
    }
    setSearching(false);   // any other destination closes the search overlay first
    const r = parse('#' + path);
    const full = r.tab === 'tactical' && !r.parts.length ? { tab: 'tactical', parts: [FK.view()] } : r;
    if (location.hash === hashOf(full) && route) return;
    if (opts && opts.replace) replace(hashOf(full)); else push(hashOf(full));
    apply(full);
  }

  /* Close the search overlay and step back off its entry, so history is exactly as it was before search opened;
     then(), if given, runs once the screen underneath is current again (or after a short wait if Back does nothing). */
  function closeSearch(then) {
    const done = typeof then === 'function' ? then : () => {};
    if (!searching || !route || !isSearchHash(location.hash)) { setSearching(false); done(); return; }
    setSearching(false);
    let ran = false;
    const once = () => { if (!ran) { ran = true; done(); } };
    afterPop.push(once);
    history.back();
    setTimeout(() => { afterPop = afterPop.filter(f => f !== once); once(); }, 500);
  }

  FK.route = { parse, go, closeSearch, current: () => route || parse(location.hash), isSearch: () => searching,
    index: () => index };   // this entry's position: leave a screen with history.go(openedAt - FK.route.index())
  addEventListener('popstate', onNavigate);
  addEventListener('hashchange', onNavigate);
  // First route replaces the entry, so opening the app adds no history. A reload on '#/search' lands on the tab underneath.
  // A reload keeps the entry's number and any other state stored on it.
  index = stateIndex() ?? 0;
  const first = apply(isSearchHash(location.hash) ? { tab: storedTab(), parts: [] } : parse(location.hash));
  replace(hashOf(first));
})();
