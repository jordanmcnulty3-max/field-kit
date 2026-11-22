/* ---------- Sheets: modal <dialog>s that own one history entry each, so Back closes them ----------
   Opening pushes a copy of history.state (the router's fkIdx stays as it is) plus fkSheet: <dialog id>.
   Back, Escape, a tap on the backdrop and the sheet's own buttons all end up in finish().
   A sheet opened with guard: { dirty(), title, text } asks before Back, Escape or a backdrop tap throws away what was typed:
   the same Keep editing / Discard confirm a route uses. Keep editing leaves the sheet open on its own entry (Back pushes the
   entry again, as a layer's onBack does); Discard closes it, through finish(), once the confirm's own step has landed. */
(() => {
  const FK = window.FK;
  const { $ } = FK;
  const stack = [];        // open sheets, bottom first: { dlg, onClose }
  const live = new Set();  // ask/confirm dialogs with a call in flight (queued or open)
  let busy = false;        // a history step we started is still on its way; opens wait for it
  let waiting = [];
  let busyTimer = 0;

  const settle = () => {
    clearTimeout(busyTimer); busy = false;
    const fns = waiting; waiting = [];
    fns.forEach(fn => { try { fn(); } catch (e) { console.error(e); } });
  };
  function step(n) {       // leave n entries; settle when the browser has moved (or after 3 s if it never does: a slow phone can take over 500 ms)
    busy = true;
    clearTimeout(busyTimer); busyTimer = setTimeout(settle, 3000);
    history.go(-n);
  }

  /* A double tap on a sheet's Save: the second tap must not land on what was under the sheet (the tab bar, the map). For
     350 ms after a sheet closes from a tap, a tap at that same spot (within 30 px) outside any open dialog is swallowed;
     a tap anywhere else goes through. */
  const QUIET_MS = 350, QUIET_PX = 30;
  let quietUntil = 0, quietAt = null, lastDown = null;
  addEventListener('pointerdown', e => { lastDown = { x: e.clientX, y: e.clientY, t: performance.now() }; }, { capture: true });
  const swallow = e => {
    if (!quietAt || performance.now() >= quietUntil) return;
    if (e.target instanceof Element && e.target.closest('dialog[open]')) return;
    const p = e.touches && e.touches[0] ? e.touches[0] : e;
    if (!Number.isFinite(p.clientX) || Math.hypot(p.clientX - quietAt.x, p.clientY - quietAt.y) > QUIET_PX) return;
    e.preventDefault(); e.stopPropagation();
  };
  ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click', 'touchstart'].forEach(t => addEventListener(t, swallow, { capture: true, passive: false }));
  const quiet = () => {
    const now = performance.now();
    if (lastDown && now - lastDown.t < 1000) { quietAt = { x: lastDown.x, y: lastDown.y }; quietUntil = now + QUIET_MS; }
  };

  function finish(entry, back) {
    const i = stack.indexOf(entry);
    if (i < 0) return;
    stack.splice(i, 1);
    entry.dlg.removeEventListener('close', entry.onNative);
    entry.dlg.removeEventListener('click', entry.onClick);
    entry.dlg.removeEventListener('pointerdown', entry.onDown);
    entry.dlg.removeEventListener('cancel', entry.onCancel);
    if (entry.dlg.open) entry.dlg.close();
    quiet();
    if (back) step(1);
    if (entry.onClose) { try { entry.onClose(); } catch (e) { console.error(e); } }
    if (!stack.length) FK.emit('sheetsClosed');   // the last open sheet has gone (its history step may still be on its way)
  }

  function open(dlg, opts) {
    if (!dlg || stack.some(e => e.dlg === dlg)) return;
    // A sheet closed with a plain dlg.close() has not been finished yet (its close event is still queued): finish it now
    // so its history entry is stepped off before this one is pushed.
    while (stack.length && !stack[stack.length - 1].dlg.open) finish(stack[stack.length - 1], true);
    if (busy) { waiting.push(() => open(dlg, opts)); return; }
    const entry = { dlg, onClose: opts && opts.onClose, guard: opts && opts.guard };
    const onOpen = opts && opts.onOpen;
    try { dlg.showModal(); }
    catch (e) { console.warn('sheet: cannot open', e); if (entry.onClose) entry.onClose(); return; }   // stack and history untouched
    /* Escape, or a plain dlg.close() somewhere else: the dialog is already closed when its close event fires. A close event
       queued by an earlier finish() of this same dialog can arrive (about 10 ms later, after the popstate) once the dialog
       has been opened again; then the dialog is open, and the event belongs to the closed entry, not this one. */
    entry.onNative = () => { if (!dlg.open) finish(entry, true); };
    /* A tap outside the sheet's box lands on the dialog element itself. A press that started inside the sheet (a drag out
       of a text field) also ends in a click on the dialog: only a press that started on the backdrop closes it. */
    const outside = e => { const r = dlg.getBoundingClientRect(); return e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom); };
    let downOut = false;
    entry.onDown = e => { downOut = outside(e); };
    entry.onClick = e => { const was = downOut; downOut = false; if (was && outside(e)) dismiss(dlg); };
    entry.onCancel = e => { if (dirty(entry)) { e.preventDefault(); askDiscard(entry); } };   // Escape (and Android Back on a dialog)
    dlg.addEventListener('close', entry.onNative);
    dlg.addEventListener('pointerdown', entry.onDown);
    dlg.addEventListener('click', entry.onClick);
    dlg.addEventListener('cancel', entry.onCancel);
    stack.push(entry);
    history.pushState({ ...(history.state && typeof history.state === 'object' ? history.state : {}), fkSheet: dlg.id }, '');
    if (onOpen) onOpen();
  }

  const dirty = entry => { try { return !!(entry.guard && entry.guard.dirty()); } catch (e) { console.error(e); return false; } };
  /* Keep editing / Discard for a guarded sheet. Discard closes the sheet (and anything above it) through close(). */
  function askDiscard(entry) {
    const g = entry.guard;
    askConfirm({ title: g.title, text: g.text || '', ok: 'Discard', cancel: 'Keep editing', danger: true })
      .then(yes => { if (yes && stack.includes(entry)) afterStep(() => close(entry.dlg)); });
  }
  /* What a person does to leave a sheet (a backdrop tap, a Cancel that should ask): asks first when the sheet is guarded and
     has unsaved changes, else closes it. */
  function dismiss(dlg) {
    const entry = stack.find(e => e.dlg === dlg);
    if (entry && dirty(entry)) { askDiscard(entry); return; }
    close(dlg);
  }

  /* Close dlg (and any sheet stacked above it) and step back off its history entry. */
  function close(dlg) {
    const i = stack.findIndex(e => e.dlg === dlg);
    if (i < 0) { if (dlg && dlg.open) dlg.close(); return; }
    const n = stack.length - i;
    const gone = stack.slice(i).reverse();
    gone.forEach(e => finish(e, false));
    step(n);
  }

  /* ---------- Layers: a screen state that is not a dialog (a map tool mode: the map must stay pannable) but that Back
     should end. layer(id, { onBack, onEnd }) pushes one history entry: a copy of history.state plus fkLayer: id, so the
     router's fkIdx arithmetic is untouched, exactly as a sheet does. Sheets opened on top copy fkLayer too, so "on the layer
     or above it" is simply history.state.fkLayer === id.
       - Back off the entry calls onBack(). Return a function to stay: the entry is pushed again and the function runs
         (open a confirm from there); return anything else to end, and onEnd('back') is called.
       - A navigation (new route, search) ends it without a history step: onEnd('nav'). Back from the new screen lands on
         the dead entry, which bounces on to the screen underneath, as for sheets.
       - handle.close() ends it from the code (Done, Cancel) once any pending sheet step has landed: sheets still open
         above the layer close with it, and history steps back off their entries and the layer's together. onEnd is not
         called. handle.active() is false from the moment it ends.
     Each call gets its own entry id (the name passed plus a number), so a stale entry of an earlier layer with the same name
     is never taken for a live one. ---------- */
  const layers = [];   // { id, onBack, onEnd, pushed, closing, depth: sheets open below the layer's entry }
  let layerSeq = 0;
  const pushLayer = l => {
    history.pushState({ ...(history.state && typeof history.state === 'object' ? history.state : {}), fkLayer: l.id }, '');
    l.pushed = true; l.depth = stack.length;
  };
  function layer(id, opts) {
    const l = { id: `${id}.${++layerSeq}`, onBack: opts && opts.onBack, onEnd: opts && opts.onEnd, pushed: false, closing: false, depth: 0 };
    layers.push(l);
    afterStep(() => {
      if (!layers.includes(l) || l.closing) { remove(l); return; }
      pushLayer(l);
    });
    return {
      active: () => layers.includes(l) && !l.closing,
      close() {
        if (!layers.includes(l) || l.closing) return;
        l.closing = true;
        afterStep(() => {
          if (!layers.includes(l)) return;
          if (!l.pushed || !history.state || history.state.fkLayer !== l.id) { remove(l); return; }   // not on it or above it
          const above = stack.slice(l.depth);   // sheets opened on top of the layer: their entries go too
          above.reverse().forEach(e => finish(e, false));
          step(1 + above.length);   // the layer is removed when the step lands
        });
      }
    };
  }
  const remove = l => { const i = layers.indexOf(l); if (i >= 0) layers.splice(i, 1); };
  const end = (l, why) => { remove(l); if (l.onEnd) { try { l.onEnd(why); } catch (e) { console.error(e); } } };
  function layersAfterPop(lid) {
    layers.slice().reverse().forEach(l => {
      if (!l.pushed || lid === l.id) return;
      if (l.closing) { remove(l); return; }
      let keep = null;
      try { keep = l.onBack ? l.onBack() : null; } catch (e) { console.error(e); }
      if (typeof keep === 'function') {
        pushLayer(l);
        try { keep(); } catch (e) { console.error(e); }
      } else end(l, 'back');
    });
  }
  function dropLayers() { layers.slice().reverse().forEach(l => { if (l.closing) remove(l); else end(l, 'nav'); }); }

  /* Back/Forward: close the sheets above the entry we landed on. The router sees the same hash and the same
     fkIdx on these entries, so it does nothing, and the screen underneath is left alone. */
  addEventListener('popstate', () => {
    const sid = history.state && history.state.fkSheet;
    const at = sid ? stack.findIndex(e => e.dlg.id === sid) : -1;
    const lid = history.state && history.state.fkLayer;
    if ((sid && at < 0) || (lid && !layers.some(l => l.id === lid))) { history.back(); return; }   // Forward onto a sheet or layer that is gone
    /* Back off one guarded sheet with unsaved changes: put its entry back and ask (the sheet itself never closed). */
    const leaving = stack.slice(at + 1);
    if (leaving.length === 1 && dirty(leaving[0]) && leaving[0].dlg.open) {
      history.pushState({ ...(history.state && typeof history.state === 'object' ? history.state : {}), fkSheet: leaving[0].dlg.id }, '');
      settle();
      askDiscard(leaving[0]);
      return;
    }
    leaving.reverse().forEach(e => finish(e, false));
    layersAfterPop(lid);   // after the sheets above have closed: a layer's onBack may open a sheet of its own
    settle();   // only now may a queued open run: it must not be closed by the pop that released it
  });
  // A reload on a sheet's entry keeps its state; the sheet itself is gone, so drop the marker.
  if (history.state && (history.state.fkSheet || history.state.fkLayer)) {
    const { fkSheet, fkLayer, ...rest } = history.state;
    history.replaceState(rest, '', location.href);
  }

  /* Navigation (a new route, or the search overlay) while sheets are open: their entries are no longer current, so close
     them without stepping history. Back from the new screen then lands on the dead entry, which bounces on to the screen. */
  const dropAll = () => { stack.slice().reverse().forEach(e => finish(e, false)); dropLayers(); };
  FK.on('route', dropAll);

  /* A navigation asked for while a sheet's history step is still on its way must wait for that step: otherwise the router
     pushes its entry first and the pending step then pops it, leaving the user on the screen they were leaving. The queued
     call runs, in order, when the step settles. router.js loads after this file, so wrap its go() the first time it reports a route.
     Callers that rely on go() running AT ONCE when no step is pending (they read or clear state straight after the call), so
     the wrap must stay synchronous in that case: protocol.js goReplace (pendingStamp) and the replace in its step render;
     emergency-tools.js opening a tool (toolOpts deleted after the call); survival.js's replace inside holdLive; search.js
     nav() followed by FK.markers.openList() or whenMap(). */
  let wrapped = false;
  const wrapGo = () => {
    if (wrapped || !FK.route) return;
    wrapped = true;
    const go = FK.route.go;
    FK.route.go = (path, opts) => { if (busy) waiting.push(() => FK.route.go(path, opts)); else go(path, opts); };
  };
  FK.on('route', wrapGo);
  FK.on('search', e => { if (e && e.open) dropAll(); });

  /* One text field in #dlgAsk. Resolves the trimmed text, or null on cancel. */
  function ask({ title, label, value = '', ok = 'Save', max = 60 }) {
    const dlg = $('#dlgAsk');
    if (live.has(dlg)) return Promise.resolve(null);   // already open or queued: leave the first call alone
    live.add(dlg);
    $('#askTitle').textContent = title;
    $('#askLabel').textContent = label;
    const input = $('#askInput'), go = $('#askOk');
    input.maxLength = max; input.value = value;
    go.textContent = ok;
    const sync = () => { go.disabled = !input.value.trim(); };
    sync();
    return new Promise(resolve => {
      let result = null;
      const submit = e => { e.preventDefault(); const t = input.value.trim(); if (!t) return; result = t; close(dlg); };
      const cancel = () => close(dlg);
      $('#askForm').onsubmit = submit;
      input.oninput = sync;
      $('#askCancel').onclick = cancel;
      open(dlg, { onClose: () => { live.delete(dlg); resolve(result); }, onOpen: () => { input.focus(); input.select(); } });
    });
  }

  /* Confirm in #dlgConfirm. Focus starts on Cancel, so a stray Enter never does the destructive thing. Resolves true (ok) or false.
     choice: true makes both buttons answers: resolves 'ok' or 'cancel' for the button pressed and null when the sheet is closed any
     other way (Back, Escape, a backdrop tap); focus then starts on the title, so a stray Enter takes neither. */
  function askConfirm({ title, text = '', ok, cancel = 'Cancel', danger = false, choice = false }) {
    const dlg = $('#dlgConfirm');
    if (live.has(dlg)) return Promise.resolve(false);
    live.add(dlg);
    $('#cfTitle').textContent = title;
    const p = $('#cfText'); p.textContent = text; p.hidden = !text;
    const go = $('#cfOk');
    go.textContent = ok; go.classList.toggle('danger', !!danger);
    $('#cfCancel').textContent = cancel;
    return new Promise(resolve => {
      let result = choice ? null : false;
      go.onclick = () => { result = choice ? 'ok' : true; close(dlg); };
      $('#cfCancel').onclick = () => { if (choice) result = 'cancel'; close(dlg); };
      open(dlg, { onClose: () => { live.delete(dlg); resolve(result); }, onOpen: () => $(choice ? '#cfTitle' : '#cfCancel').focus() });
    });
  }

  /* Run fn once any history step a sheet started has landed (at once if none is on its way). Use it to close a second sheet
     straight after a stacked one has closed: two steps back in the same moment can collapse into one. */
  const afterStep = fn => { if (busy) waiting.push(fn); else fn(); };

  FK.sheet = { open, close, dismiss, ask, confirm: askConfirm, afterStep, layer, top: () => stack.length ? stack[stack.length - 1].dlg : null };
})();
