/* ---------- Survival tools: ordinary Survival pages at #/survival/tool/<name>, key u:<name>. Adding a tool is one entry in TOOLS. ---------- */
(() => {
  const FK = window.FK;

  /* name -> { label, keywords?, draw(el) }. draw fills el and may return a function that undoes everything it started;
     survival.js calls that on every way of leaving the page (Back, tab switch, opening another page). */
  const TOOLS = {
    sos: { label: 'SOS light', keywords: 'morse signal distress flash flashlight rescue screen light', draw: drawSos }
  };

  /* ---------- SOS light ---------- */
  const UNIT_MS = 200;
  /* Morse S O S in units, alternating on and off and starting on: ... --- ... then 7 units off before it repeats. */
  const SOS_UNITS = [1, 1, 1, 1, 1, 3, 3, 1, 3, 1, 3, 3, 1, 1, 1, 1, 1, 7];
  const WARNING = 'A flashing screen can be seen from far away and gives away your position.';

  function drawSos(el) {
    el.innerHTML = '<p class="sv-warn"><strong>Warning:</strong> ' + FK.esc(WARNING) + '</p>' +
      '<div class="sv-sos-btns"><button type="button" class="btn" id="svSosStart" aria-describedby="svSosNote">Start SOS</button>' +
      '<button type="button" class="btn ghost" id="svSosSteady">Steady light</button></div>' +
      '<p id="svSosNote" class="sv-cnote">Flashes the whole screen white in Morse S O S, or holds it steadily lit, and keeps the screen awake. ' +
      'Reduced motion settings do not change the flashing: it is how the light signals. Tap the screen to stop.</p>' +
      '<button type="button" class="sv-light" hidden data-on="0" aria-label="Stop the light"><span>Tap to stop</span></button>';
    const startBtn = el.querySelector('#svSosStart'), steadyBtn = el.querySelector('#svSosSteady'), panel = el.querySelector('.sv-light');
    let running = false, timer = null, opener = null, lock = null, lockPending = false;

    /* Screen wake lock, the same guards as the protocol player: no API, a refused request or a stop before it answers all leave the screen as it was. */
    async function wakeOn() {
      if (lock || lockPending || !running || document.hidden || !navigator.wakeLock) return;
      lockPending = true;
      try {
        const l = await navigator.wakeLock.request('screen');
        if (!running) { l.release().catch(() => {}); return; }
        lock = l;
        l.addEventListener('release', () => { if (lock === l) lock = null; });
      } catch { /* denied: the screen times out as usual */ }
      finally { lockPending = false; }
    }
    function wakeOff() { if (lock) { const l = lock; lock = null; l.release().catch(() => {}); } }

    const light = on => { panel.dataset.on = on ? '1' : '0'; };
    function flash(i) {
      light(i % 2 === 0);
      timer = setTimeout(() => flash((i + 1) % SOS_UNITS.length), SOS_UNITS[i] * UNIT_MS);
    }
    function begin(steady, from) {
      if (running) return;
      running = true; opener = from;
      startBtn.textContent = 'Stop SOS';
      panel.hidden = false;
      document.addEventListener('visibilitychange', onVisibility);
      wakeOn();
      if (steady) light(true); else flash(0);
      panel.focus();
    }
    function end(refocus) {
      if (!running) return;
      running = false;
      clearTimeout(timer); timer = null;
      document.removeEventListener('visibilitychange', onVisibility);
      wakeOff();
      light(false);
      panel.hidden = true;
      startBtn.textContent = 'Start SOS';
      if (refocus && opener && opener.isConnected) opener.focus();
      opener = null;
    }
    function onVisibility() { if (document.hidden) end(true); }   // a hidden tab cannot show the light, so it stops rather than flash unseen

    startBtn.addEventListener('click', () => { if (running) end(true); else begin(false, startBtn); });
    steadyBtn.addEventListener('click', () => begin(true, steadyBtn));
    panel.addEventListener('click', () => end(true));
    return () => end(false);
  }

  /* ---------- Registration ---------- */
  FK.survival.tools = () => Object.entries(TOOLS).map(([name, t]) => ({ name, label: t.label, ...(t.keywords ? { keywords: t.keywords } : {}) }));
  FK.survival.registerPage('tool', (name, el) => {
    if (!Object.hasOwn(TOOLS, name)) return false;
    const t = TOOLS[name];
    el.innerHTML = '<article class="sv-page" data-tool="' + FK.esc(name) + '">' + FK.survival.headHTML('u:' + name, { title: t.label }) + '<div class="sv-tool"></div></article>';
    const out = t.draw(el.querySelector('.sv-tool'));
    FK.recent.add('u:' + name);
    return typeof out === 'function' ? out : undefined;
  });
  FK.survival.homeItems('tool', () => FK.survival.tools().map(t => ({ key: 'u:' + t.name, title: t.label })));
})();
