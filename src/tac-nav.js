/* ---------- Navigate display: the panel at the top of Position, the strip on the map, route stepping, time to go and
   Back to start. The target itself is FK.tac's (tac-data.js); GPS follows it in app.js. ----------
   TNAV holds the rules as plain functions of plain values (no DOM), so they can be tested on their own. */
const TNAV = (() => {
  const norm = d => ((d % 360) + 360) % 360;
  /* The turn from the heading to the bearing, the short way: -180 < a <= 180, positive to the right. */
  function turnAngle(brg, hdg) { const a = norm(brg - hdg); return a > 180 ? a - 360 : a; }
  function turnText(brg, hdg) {
    const a = turnAngle(brg, hdg), n = Math.round(Math.abs(a));
    if (n <= 5) return 'Straight ahead';
    return `Turn ${n}° ${a > 0 || n === 180 ? 'right' : 'left'}`;
  }
  /* A marker or point counts as reached within this many metres. An unknown accuracy gets the smallest radius. */
  const arriveRadius = acc => Number.isFinite(acc) ? Math.max(15, Math.min(acc, 50)) : 15;
  /* A route point counts as reached within this many metres; a fix worse than 100 m (or without an accuracy) never reaches one. */
  const advanceRadius = acc => Number.isFinite(acc) && acc <= 100 ? Math.max(25, acc) : null;

  /* Closing speed toward the target in m/s: how fast the distance to it is shrinking, which is what time to go depends on.
     Fixes are {lat, lon, t, acc}. The window is the fixes of the 60 s up to the newest fix; only fixes with accuracy 50 m or
     better are kept, so a poor or unknown one leaves a gap. At least 6 kept fixes over at least 30 s, no gap over 15 s
     between kept fixes, nor between the newest kept fix and the newest fix of all. Only the two ends count, so GPS jitter in
     between adds nothing; each end is the median position of its three fixes (taken at the middle one's time), so one wild
     end fix can't decide it. null when the fixes can't support a figure; negative when moving away. */
  const WINDOW = 60000, MIN_SPAN = 30000, MIN_FIXES = 6, MAX_GAP = 15000, MAX_ACC = 50;
  const median3 = a => a.slice().sort((x, y) => x - y)[1];
  const endOf = three => ({ lat: median3(three.map(f => f.lat)), lon: median3(three.map(f => f.lon)), t: three[1].t });
  /* The two median ends: how many metres nearer the target the newer one is (m) and over how many seconds (s); and the
     scatter (sd): the standard deviation of the kept fixes' distances to the target around their least-squares line against
     time, which is how noisy this phone's fixes are just now. */
  function ends(fixes, target) {
    if (!target || !Number.isFinite(target.lat) || !Number.isFinite(target.lon)) return null;
    const all = (fixes || []).filter(f => f && Number.isFinite(f.t) && Number.isFinite(f.lat) && Number.isFinite(f.lon)).sort((a, b) => a.t - b.t);
    if (!all.length) return null;
    const newest = all[all.length - 1].t;
    const kept = all.filter(f => f.t >= newest - WINDOW && Number.isFinite(f.acc) && f.acc <= MAX_ACC);
    if (kept.length < MIN_FIXES || newest - kept[kept.length - 1].t > MAX_GAP) return null;
    if (kept[kept.length - 1].t - kept[0].t < MIN_SPAN) return null;
    for (let i = 1; i < kept.length; i++) if (kept[i].t - kept[i - 1].t > MAX_GAP) return null;
    const n = kept.length;
    const a = endOf(kept.slice(0, 3)), b = endOf(kept.slice(n - 3));
    if (!(b.t > a.t)) return null;
    const da = GEO.distance(a.lat, a.lon, target.lat, target.lon), db = GEO.distance(b.lat, b.lon, target.lat, target.lon);
    const d = kept.map(f => GEO.distance(f.lat, f.lon, target.lat, target.lon)), t = kept.map(f => (f.t - kept[0].t) / 1000);
    const tm = t.reduce((x, y) => x + y) / n, dm = d.reduce((x, y) => x + y) / n;
    let sxx = 0, sxy = 0, rss = 0;
    for (let i = 0; i < n; i++) { sxx += (t[i] - tm) ** 2; sxy += (t[i] - tm) * (d[i] - dm); }
    const slope = sxy / sxx;
    for (let i = 0; i < n; i++) rss += (d[i] - dm - slope * (t[i] - tm)) ** 2;
    return { m: da - db, s: (b.t - a.t) / 1000, sd: Math.sqrt(rss / (n - 2)) };
  }
  const closing = (fixes, target) => { const e = ends(fixes, target); return e ? e.m / e.s : null; };
  /* Whether a time to go shows, with one boolean of memory: was a time showing a moment ago (on)?
     It STARTS only when the ends are at least max(30 m, 4 x scatter) nearer the target, so GPS scatter at a standstill can't
     pass for progress, at 0.5 to 12 m/s. Once showing it STAYS while they are at least max(20 m, 2.5 x scatter) nearer at
     0.35 to 12 m/s, so a walker's time doesn't flicker on and off at the threshold. Every window rule above holds throughout.
     The caller turns `on` off when the target changes or there is no fresh fix. Returns { on, v }: v the closing speed when on. */
  const START = { m: 30, k: 4, v: 0.5 }, KEEP = { m: 20, k: 2.5, v: 0.35 }, MAX_V = 12;
  function timeGate(fixes, target, on) {
    const e = ends(fixes, target);
    if (!e) return { on: false, v: null };
    const r = on ? KEEP : START, v = e.m / e.s;
    const ok = e.m >= Math.max(r.m, r.k * e.sd) && v >= r.v && v <= MAX_V;
    return { on: ok, v: ok ? v : null };
  }
  /* Moving away from the target: the mirror of a time that stays showing. The ends are at least max(20 m, 2.5 x scatter)
     FURTHER from it, at 0.35 m/s or more, under every window rule above. A walker who has passed a route point sees this. */
  function away(fixes, target) {
    const e = ends(fixes, target);
    if (!e) return false;
    const m = -e.m, v = m / e.s;
    return m >= Math.max(KEEP.m, KEEP.k * e.sd) && v >= KEEP.v && v <= MAX_V;
  }
  /* The speed a time would START from (no time showing before), or null. */
  const pace = (fixes, target) => timeGate(fixes, target, false).v;
  function timeText(m, v) {
    const s = Math.round(m / v);
    if (s < 60) return 'under 1 min';
    const min = Math.ceil(s / 60);
    if (min <= 120) return `about ${min} min`;
    return min % 60 ? `about ${Math.floor(min / 60)} h ${min % 60} min` : `about ${min / 60} h`;
  }
  /* How old the position is, once it is old enough to make the arrow wrong (over 30 s); '' before that. */
  function ageShort(ms) {
    if (!(ms > 30000)) return '';
    if (ms <= 90000) return `${Math.floor(ms / 1000)} s`;
    const min = Math.round(ms / 60000);
    return min <= 90 ? `${min} min` : `${Math.round(ms / 3600000)} h`;
  }
  const ageText = ms => { const a = ageShort(ms); return a ? `Position is ${a} old` : ''; };
  return { away, turnAngle, turnText, arriveRadius, advanceRadius, closing, pace, timeGate, scatter: (f, t) => { const e = ends(f, t); return e ? e.sd : null; }, START, KEEP, timeText, ageText, ageShort, STALE_MS: 30000, WINDOW };
})();

(() => {
  const FK = window.FK;
  const { $, on, toast } = FK;
  const el = id => document.getElementById(id);
  const panel = el('navPanel'), strip = el('navStrip'), awayBox = el('nsAway'), act = el('nvAct'), prev = el('nvPrev'), next = el('nvNext');
  const wake = el('wakeBtn'), wakeHome = wake.parentElement, wakeAfter = wake.nextSibling;
  const fmt = m => TGEOM.fmtDist(m, FK.tac.unit());
  const LIVE_MS = 5000;
  let buf = [];               // recent live fixes {lat, lon, t, acc}, for the closing speed
  let rot = null;             // the arrow's rotation so far, so it turns the short way across north
  let timer = null, liveText = '', liveAt = -Infinity;
  let timeOn = false;         // is a time to go showing (TNAV.timeGate's one bit of memory)

  /* Redraws change text and attributes only: the buttons are never rebuilt, so a tap or focus survives a redraw. */
  const show = (e, on) => { if (on) e.removeAttribute('hidden'); else if (!e.hasAttribute('hidden')) e.setAttribute('hidden', ''); };
  const text = (e, t) => { if (e.textContent !== t) e.textContent = t; };
  const attr = (e, k, v) => { if (e.getAttribute(k) !== v) e.setAttribute(k, v); };
  const line = (id, t) => { const e = el(id); text(e, t || ''); show(e, !!t); };

  /* One Keep screen on button: it moves into the panel while a target is set and back beside Declination after. */
  function placeWake(inPanel) {
    if (inPanel && wake.parentElement !== act) { act.appendChild(wake); wakeHome.hidden = true; }
    else if (!inPanel && wake.parentElement !== wakeHome) { wakeHome.insertBefore(wake, wakeAfter); wakeHome.hidden = false; }
  }

  function routePts(t) { const s = t && t.type === 'route' && FK.tac.shapes().find(x => x.id === t.id); return s ? s.pts : null; }

  function renderBack() {
    const s = FK.isRecording && FK.isRecording() && FK.map && FK.map.trackStart();
    show(el('nvBackWrap'), !!s);
    show(el('trkBackRow'), !!s);
  }

  function announce(t, now) {
    if (t === liveText || now - liveAt < LIVE_MS) return;
    liveText = t; liveAt = now;
    text(el('nvLive'), t);
  }

  function render() {
    renderBack();
    const t = FK.tac.target(), w = FK.tac.targetPoint(), mark = el('tgtMark');
    placeWake(!!w);
    show(panel, !!w);
    show(strip, !!w);
    if (!w) { show(mark, false); show(awayBox, false); rot = null; timeOn = false; return; }
    const f = FK.getFix(), now = Date.now(), step = w.step;
    text(el('nvName'), w.name);
    text(el('nsName'), w.name);
    show(el('nvStep'), !!step);
    show(el('nsStep'), !!step);
    if (step) {
      text(el('nvStepText'), `Point ${step[0] + 1} of ${step[1]}`);
      text(el('nsStep'), `${step[0] + 1}/${step[1]}`);
      attr(prev, 'aria-disabled', String(step[0] === 0));
      attr(next, 'aria-disabled', String(step[0] === step[1] - 1));
    }
    show(el('nvWait'), !f);
    show(el('nsWait'), !f);
    const live = step ? `Point ${step[0] + 1} of ${step[1]}. ` : '';
    if (!f) {
      ['nvDist', 'nvBrg', 'nvArrived', 'nvAge', 'nvTurn', 'nvNoCompass', 'nvAskWrap', 'nvTime', 'nvEnd', 'nvArrow', 'nsDist', 'nsBrg', 'nvAway', 'nsAway'].forEach(id => show(el(id), false));
      show(mark, false); rot = null; timeOn = false;
      attr(strip, 'aria-label', `${w.name}: waiting for a position. Open Position.`);
      announce(live + 'Waiting for a position', now);
      return;
    }
    const d = GEO.distance(f.lat, f.lon, w.lat, w.lon), b = GEO.bearing(f.lat, f.lon, w.lat, w.lon);
    const deg = Math.round(b) % 360, dist = fmt(d), brg = `${deg}° true`;
    const age = now - f.t, stale = !(age <= TNAV.STALE_MS);
    const r = step ? TNAV.advanceRadius(f.acc) : TNAV.arriveRadius(f.acc);
    const arrived = !stale && r != null && d <= r && (!step || step[0] === step[1] - 1);   // never decided from an old position
    line('nvDist', dist); line('nvBrg', brg);
    show(el('nvArrived'), arrived);
    line('nvAge', TNAV.ageText(age));
    const old = TNAV.ageShort(age);   // an old position is not shown on the strip as if it were current
    line('nsDist', arrived ? 'Arrived' : old ? `${dist}, ${old} old` : dist); line('nsBrg', arrived ? '' : `${deg}°`);
    /* Passed the point and walking on: say so here and on the map, where Next and Stop are one tap away too. */
    const off = !stale && !arrived && TNAV.away(buf, w);
    const offText = off ? `Moving away from ${step ? 'point ' + (step[0] + 1) : w.name}` : '';
    line('nvAway', offText);
    text(el('nsAwayText'), offText);
    show(awayBox, off);
    show(el('nsNext'), off && !!step && step[0] < step[1] - 1);
    el('nsRest').classList.toggle('old', !!old);
    attr(strip, 'aria-label', `${step ? `Point ${step[0] + 1} of ${step[1]}, ` : ''}${w.name}: ${dist} at ${brg}${old ? `, from a position ${old} old` : ''}. Open Position.`);
    show(mark, true);
    attr(mark, 'transform', `rotate(${b} 100 100)`);

    const h = FK.trueHeading(), arrow = el('nvArrow');
    let turn = '';
    if (h == null || arrived) { show(arrow, false); rot = null; }   // inside the arrival radius the bearing is noise
    else {
      const want = TNAV.turnAngle(b, h);
      rot = rot == null ? want : rot + TNAV.turnAngle(want, rot);
      el('nvArrowG').style.transform = `rotate(${rot}deg)`;
      show(arrow, true);
      turn = TNAV.turnText(b, h);
    }
    line('nvTurn', turn);
    show(el('nvNoCompass'), h == null);
    show(el('nvAskWrap'), h == null && FK.compassAsk());   // iPhone before motion permission: Turn on compass

    let v = null;
    if (stale || arrived) timeOn = false;
    else { const g = TNAV.timeGate(buf, w, timeOn); timeOn = g.on; v = g.v; }
    line('nvTime', v ? TNAV.timeText(d, v) : '');
    const pts = step && step[0] < step[1] - 1 ? routePts(t) : null;
    line('nvEnd', pts ? `${fmt(d + TGEOM.pathLength(pts.slice(step[0])))} to the end` : '');

    announce(`${live}${arrived ? 'Arrived. ' : ''}${dist}, ${brg}${turn ? '. ' + turn : ''}`, now);
  }

  /* A route moves on by one point per fix at most, and only from the point it is on: passing near a later point does not skip. */
  function advance(f) {
    if (!(Date.now() - f.t <= TNAV.STALE_MS)) return;   // never from an old position
    const t = FK.tac.target(), w = FK.tac.targetPoint();
    if (!t || t.type !== 'route' || !w || !w.step || w.step[0] >= w.step[1] - 1) return;
    const r = TNAV.advanceRadius(f.acc);
    if (r == null || GEO.distance(f.lat, f.lon, w.lat, w.lon) > r) return;
    FK.tac.setTarget({ type: 'route', id: t.id, i: t.i + 1 });
  }

  function onFix(f) {
    if (f && Number.isFinite(f.t)) {
      if (buf.length && f.t < buf[buf.length - 1].t) buf = [];   // time went backwards: start the pace again
      buf.push({ lat: f.lat, lon: f.lon, t: f.t, acc: f.acc });
      buf = buf.filter(p => p.t >= f.t - TNAV.WINDOW);
    }
    if (f) advance(f);
    render();
  }

  /* One timer, while a target is set and the page shows: it keeps the position's age current. */
  function syncTimer() {
    const want = !!FK.tac.target() && !document.hidden;
    if (want && timer === null) timer = setInterval(render, 1000);
    else if (!want && timer !== null) { clearInterval(timer); timer = null; }
  }

  function step(by) {
    const t = FK.tac.target(), w = FK.tac.targetPoint();
    if (!t || t.type !== 'route' || !w || !w.step) return;
    const i = Math.max(0, Math.min(w.step[1] - 1, t.i + by));
    if (i !== t.i) FK.tac.setTarget({ type: 'route', id: t.id, i });
  }
  el('nsNext').addEventListener('click', () => step(1));
  el('nsStop').addEventListener('click', () => { FK.tac.setTarget(null); FK.refocus(null); });
  prev.addEventListener('click', () => step(-1));
  next.addEventListener('click', () => step(1));
  el('nvStop').addEventListener('click', () => { FK.tac.setTarget(null); FK.refocus(null); });
  function backToStart() {
    const s = FK.isRecording() && FK.map.trackStart();
    return !!s && FK.tac.setTarget({ type: 'point', lat: s.lat, lon: s.lon, name: 'Start' });
  }
  el('nvBack').addEventListener('click', backToStart);
  el('trkBack').addEventListener('click', () => {
    if (!backToStart()) return;
    FK.sheet.close($('#dlgTrack'));
    toast('Back to Start. Open Position for the arrow.');
  });
  strip.addEventListener('click', () => FK.route.go('/tactical/position'));
  on('decl', render);   // the heading is true heading: it moves with the declination (typed, switched or worked out)

  on('fix', onFix);
  on('target', () => { timeOn = false; syncTimer(); render(); });   // a new target, Next, Previous, advance or Stop
  ['heading', 'compassAsk', 'unit', 'wps', 'shapes', 'track'].forEach(ev => on(ev, render));
  document.addEventListener('visibilitychange', () => { syncTimer(); render(); });


  FK.nav = { ticking: () => timer !== null };
  render();
  syncTimer();
})();
