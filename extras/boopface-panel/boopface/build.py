#!/usr/bin/env python3
"""BoopFace page builder: face + skin browser (🎨) + settings (⚙️) driven by the library's own options.

The settings sheet exposes exactly what BoopFace documents in its README/index.d.ts:
size, color, auto-sleep, wake-on, motion, press-squeeze, antenna-drag, skin, plus the runtime
calls setPointerFollow() and setHeadRoundness().

Persistence: the widget runs in a sandboxed iframe with an opaque origin, so it has no storage and
no network — a change made on the phone lives until the panel reloads. This script bakes the saved
values into the widget HTML, which is what survives.

  python3 boopface-build.py                                  # reinstall with the saved settings
  python3 boopface-build.py --set motion=reduce --set autoSleep=60000
  python3 boopface-build.py --set skin=305 --set color=#ff8a65
"""
import json
import pathlib
import sys
import urllib.request

AGENT = "http://127.0.0.1:8765"
HERE = pathlib.Path(__file__).parent
BUNDLE = HERE / "boopface.iife.js"
SETTINGS = HERE / "boopface-settings.json"

DEFAULTS = {
    "skin": 902,
    "color": "#2dd4bf",
    "size": 0.86,
    "autoSleep": 45000,
    "wakeOn": "activity",
    "motion": "auto",
    "pointerFollow": False,
    "roundness": None,
    "pressSqueeze": False,
    "antennaDrag": False,
}

TEMPLATE = """<style>
  *{-webkit-tap-highlight-color:transparent}
  html,body{height:100%;margin:0;background:transparent;overflow:hidden;
    display:grid;place-items:center;transition:opacity .6s;
    -webkit-touch-callout:none;user-select:none;-webkit-user-select:none;
    font-family:Roboto,system-ui,sans-serif}
  #stage{display:grid;place-items:center}
  boop-face#avatar{touch-action:none}
  #tools{position:fixed;right:10px;bottom:10px;display:flex;gap:6px}
  #tools button{width:34px;height:34px;border-radius:17px;border:1px solid rgba(42,48,58,.7);
    background:rgba(23,27,33,.55);color:#8a94a3;font-size:15px;line-height:1;padding:0;opacity:.55}
  .panel{position:fixed;inset:0;background:rgba(8,10,13,.96);display:none;flex-direction:column;z-index:5}
  .panel.open{display:flex}
  #skins{z-index:6}
  .bar{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid #20262e}
  .bar b{font-size:13px;color:#e8ecf1;font-weight:600;flex:1}
  .bar button{border:1px solid #2a303a;background:#171b21;color:#e8ecf1;border-radius:12px;
    height:30px;padding:0 12px;font-size:12px}
  #list,#form{overflow-y:auto;padding:8px 12px 24px}
  .ser{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.08em;margin:14px 0 6px}
  .grid{display:flex;flex-wrap:wrap;gap:8px}
  .cell{width:64px;height:64px;border-radius:12px;border:1px solid #262b34;background:#12161b;
    padding:0;overflow:hidden;display:grid;place-items:center}
  .cell.on{border-color:#2dd4bf;box-shadow:0 0 0 1px #2dd4bf inset}
  .row{display:flex;align-items:center;gap:10px;padding:10px 2px;border-bottom:1px solid #1b2027}
  .row label{flex:1;font-size:13px;color:#c9d2de}
  .row small{display:block;color:#6b7280;font-size:11px;margin-top:2px}
  .row select,.row input[type=number]{background:#171b21;border:1px solid #2a303a;color:#e8ecf1;
    border-radius:10px;height:30px;padding:0 8px;font-size:12px;min-width:110px}
  .row input[type=range]{width:130px}
  .sw{display:flex;gap:6px;flex-wrap:wrap}
  .sw button{width:26px;height:26px;border-radius:13px;border:2px solid transparent;padding:0}
  .sw button.on{border-color:#e8ecf1}
  .swi{display:flex;gap:6px}
  .swi button{width:44px;height:26px;border-radius:13px;border:1px solid #2a303a;background:#171b21;
    color:#8a94a3;font-size:11px}
  .swi button.on{border-color:#2dd4bf;color:#2dd4bf}
  /* while music plays the whole face breathes with it: a 3 % bob at 120 BPM and a soft glow
     behind the head. Purely rhythmic — the widget has no audio levels to follow. */
  body.playing #stage{animation:bob 500ms ease-in-out infinite alternate}
  @keyframes bob{from{transform:scale(1)}to{transform:scale(1.03)} }
  /* aura: a halo OUTSIDE the head, not a fill behind it. The head is ~821 px on this panel,
     so a centred radial gradient at 82vmin put every visible stop behind the silhouette —
     that is why the first two versions looked invisible even though they rendered. */
  #aura{position:fixed;left:50%;top:50%;pointer-events:none;z-index:0;
    width:112vmin;aspect-ratio:1;border-radius:50%;transform:translate(-50%,-50%);
    background:conic-gradient(from 0deg,rgba(20,255,222,.85),rgba(122,92,255,.75),rgba(255,64,158,.65),
      rgba(255,196,64,.55),rgba(20,255,222,.85));
    -webkit-mask:radial-gradient(closest-side,transparent 50%,#000 58%,#000 66%,transparent 78%);
    mask:radial-gradient(closest-side,transparent 50%,#000 58%,#000 66%,transparent 78%);
    animation:auraspin 16s linear infinite,glowpulse 1s ease-in-out infinite alternate}
  @keyframes auraspin{from{transform:translate(-50%,-50%) rotate(0deg)}
    to{transform:translate(-50%,-50%) rotate(360deg)} }
  @keyframes glowpulse{from{opacity:.55}to{opacity:1} }
  #stage{position:relative;z-index:1}
  /* equalizer under the chin while something is playing (decorative: the widget gets
     media.playing, not audio levels, so these follow a rhythm, not the song) */
  #eq{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);display:none;align-items:flex-end;
    gap:5px;height:calc(14px + 22px * var(--amp,.8));z-index:3;transition:height .35s ease;
    filter:drop-shadow(0 1px 4px rgba(0,0,0,.5))}
  #eq i{display:block;width:6px;border-radius:3px;height:22%;
    background:linear-gradient(180deg,#5eead4,#2dd4bf);
    animation:eqbar 500ms ease-in-out infinite alternate}
  /* durations are multiples of 125 ms, so they land on the same 120 BPM grid as the bob */
  #eq i{width:5px;border-radius:2.5px}
  #eq i:nth-child(1){animation-duration:500ms;animation-delay:0ms}
  #eq i:nth-child(2){animation-duration:625ms;animation-delay:-125ms}
  #eq i:nth-child(3){animation-duration:750ms;animation-delay:-250ms}
  #eq i:nth-child(4){animation-duration:875ms;animation-delay:-375ms}
  #eq i:nth-child(5){animation-duration:1000ms;animation-delay:-500ms}
  #eq i:nth-child(6){animation-duration:1125ms;animation-delay:-625ms}
  #eq i:nth-child(7){animation-duration:500ms;animation-delay:-125ms}
  #eq i:nth-child(8){animation-duration:750ms;animation-delay:-375ms}
  #eq i:nth-child(9){animation-duration:875ms;animation-delay:-250ms}
  #eq i:nth-child(10){animation-duration:625ms;animation-delay:-500ms}
  #eq i:nth-child(11){animation-duration:1000ms;animation-delay:-125ms}
  #eq i:nth-child(12){animation-duration:750ms;animation-delay:-625ms}
  #eq.muted i{background:#5b6470;height:14%;animation-play-state:paused}
  @keyframes eqbar{from{height:18%}to{height:100%} }
  /* battery above the head: only when it is low and unplugged */
  #batt{position:fixed;top:9px;left:50%;transform:translateX(-50%);display:none;align-items:center;
    filter:drop-shadow(0 1px 3px rgba(0,0,0,.55));z-index:4}
  #batt.on{display:flex}
  #batt .shell{width:52px;height:22px;border:2px solid #8a94a3;border-radius:5px;padding:2px}
  #batt .cap{width:4px;height:9px;background:#8a94a3;border-radius:0 2px 2px 0}
  #batt .fill{height:100%;width:0%;background:#8a94a3;border-radius:2px;transition:width .4s ease,background .4s ease}
  #batt.warn .shell{border-color:#ffb74d} #batt.warn .cap{background:#ffb74d} #batt.warn .fill{background:#ffb74d}
  #batt.err .shell{border-color:#ff5252} #batt.err .cap{background:#ff5252} #batt.err .fill{background:#ff5252}
  #batt.err{animation:battpulse 1.1s ease-in-out infinite}
  @keyframes battpulse{0%,100%{opacity:1}50%{opacity:.3} }
  #toast{position:fixed;top:10px;left:50%;transform:translateX(-50%);background:rgba(23,27,33,.92);
    border:1px solid #2a303a;color:#e8ecf1;font-size:12px;padding:6px 12px;border-radius:14px;
    opacity:0;transition:opacity .25s;pointer-events:none;z-index:9}
  #toast.show{opacity:1}
  .fail{position:fixed;inset:auto 0 8px;text-align:center;font-size:12px;color:#8a94a3}
</style>
<div id="aura" style="display:none"></div>
<div id="stage"><boop-face id="avatar" press-squeeze="false" antenna-drag="false"></boop-face></div>
<div id="batt"><div class="shell"><div class="fill"></div></div><div class="cap"></div></div>
<div id="eq" style="display:none"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
<div id="tools"><button id="pick" title="skins">🎨</button><button id="gear" title="settings">⚙️</button></div>
<div id="skins" class="panel" style="display:none"><div class="bar"><b>Skin</b><button id="skinsClose">close</button></div><div id="list"></div></div>
<div id="settings" class="panel" style="display:none"><div class="bar"><b>BoopFace</b><button id="setClose">close</button></div><div id="form"></div></div>
<div id="toast"></div>
<script>{bundle}</script>
<script type="module">
const a = document.getElementById('avatar');
const listEl = document.getElementById('list');
const formEl = document.getElementById('form');
const skinsEl = document.getElementById('skins');
const settingsEl = document.getElementById('settings');
const toast = document.getElementById('toast');
const CFG = {cfg};
const S = Object.assign({{}}, CFG);

const fit = () => {
  const box = Math.min(innerWidth, innerHeight * 0.94) * 0.94 * (Number(S.size) || 0.86);
  a.setAttribute('size', String(Math.round(Math.max(64, box))));
};
fit(); addEventListener('resize', fit);

if (!customElements.get('boop-face')) {
  for (const url of ['https://cdn.jsdelivr.net/npm/boopface@0.8.0/+esm',
                     'https://unpkg.com/boopface@0.8.0/boopface.js']) {
    try { await import(url); break; } catch (e) { console.warn('boopface:', url, e.message); }
  }
}
if (!customElements.get('boop-face'))
  document.body.insertAdjacentHTML('beforeend', '<p class="fail">avatar unavailable</p>');
try { await window.BoopFace?.loadSkins?.(); } catch (e) { console.warn('skins:', e.message); }

if (S.roundness === null || S.roundness === undefined) {
  try { S.roundness = a.getHeadRoundness?.() ?? 0.5; } catch (e) {}
  CFG.roundness = S.roundness; // same value, so it is not a change
}

const h = new Date().getHours();
if (h >= 23 || h < 7) document.body.style.opacity = '0.55';

let mode = 'idle', skin = S.skin, toastTimer = 0, alert = '', playing = null, balance = '', battery = '', battLevel = 0;
// what the face shows when nothing else is happening: an empty wallet or a dying phone
const worry = () => (battery === 'err' || balance === 'err') ? 'failure'
  : (battery === 'warn' || balance === 'warn') ? 'wary' : 'idle';
let online = true, lastState = 0;
const eqEl = document.getElementById('eq');
const auraEl = document.getElementById('aura');
const battEl = document.getElementById('batt');
const battFill = battEl ? battEl.querySelector('.fill') : null;
const paintBattery = () => {
  if (!battEl || !battFill) return;
  battEl.classList.toggle('on', battery !== '');
  battEl.classList.toggle('warn', battery === 'warn');
  battEl.classList.toggle('err', battery === 'err');
  if (battery !== '') battFill.style.width = Math.max(6, Math.min(100, battLevel)) + '%';
};
const say = (t) => {
  toast.textContent = t; toast.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove('show'), 1600);
};

const apply = () => {
  ['color', 'auto-sleep', 'wake-on', 'motion'].forEach((k) => {
    const v = S[{{'color':'color','auto-sleep':'autoSleep','wake-on':'wakeOn','motion':'motion'}}[k]];
    if (v !== null && v !== undefined) a.setAttribute(k, String(v));
  });
  a.style.pointerEvents = (S.pressSqueeze || S.antennaDrag) ? 'auto' : 'none';
  try { a.setPressSqueeze?.(!!S.pressSqueeze); } catch (e) {{}}
  try { a.setAntennaDrag?.(!!S.antennaDrag); } catch (e) {{}}
  try { a.setPointerFollow?.(!!S.pointerFollow); } catch (e) {{}}
  if (S.roundness !== null && S.roundness !== undefined) {{ try {{ a.setHeadRoundness?.(Number(S.roundness)); }} catch (e) {{}} }}
  try {{ a.setSkin(S.skin ? Number(S.skin) : null); skin = S.skin || null; }} catch (e) {{ console.warn(e); }}
  fit();
};

const mark = (n) => {
  listEl.querySelectorAll('.cell').forEach((b) => b.classList.toggle('on', Number(b.dataset.n) === n));
};
const applySkin = (n) => {
  S.skin = n; apply(); mark(n);
  say('skin ' + n);
};

/* ---------- skin browser: real avatars, mounted only while on screen ---------- */
const groups = (() => {
  try {
    const s = window.BoopFace?.SKIN_SERIES;
    if (Array.isArray(s) && s.length) return s.map((g) => ({
      title: g.titleEn || g.title || String(g.id || g.number || ''),
      skins: (g.skins || []).map((x) => (x && typeof x === 'object') ? (x.number ?? x.id) : x)
    }));
  } catch (e) {{ console.warn(e); }}
  return [];
})();

const io = new IntersectionObserver((entries) => {
  for (const en of entries) {
    const cell = en.target;
    if (en.isIntersecting) {
      if (cell.firstElementChild) continue;
      const mini = document.createElement('boop-face');
      mini.setAttribute('size', '56');
      mini.setAttribute('motion', 'reduce');
      mini.setAttribute('auto-sleep', '0');
      mini.setAttribute('wake-on', 'manual');
      mini.setAttribute('press-squeeze', 'false');
      mini.setAttribute('antenna-drag', 'false');
      cell.append(mini);
      try {{ mini.setSkin(Number(cell.dataset.n)); mini.setPointerFollow?.(false); }} catch (e) {{}}
    }} else cell.replaceChildren();
  }}
}}, {{ root: listEl, rootMargin: '120px' }});

let built = false;
const buildSkins = () => {
  if (built) return; built = true;
  if (!groups.length) {{ listEl.textContent = 'skin catalog unavailable'; return; }}
  const frag = document.createDocumentFragment();
  for (const g of groups) {
    const h3 = document.createElement('div'); h3.className = 'ser'; h3.textContent = g.title;
    const grid = document.createElement('div'); grid.className = 'grid';
    for (const n of g.skins) {
      if (n == null) continue;
      const cell = document.createElement('button');
      cell.className = 'cell'; cell.dataset.n = String(n);
      cell.onclick = () => applySkin(Number(n));
      grid.append(cell);
    }
    frag.append(h3, grid);
  }
  listEl.append(frag);
  listEl.querySelectorAll('.cell').forEach((c) => io.observe(c));
  mark(Number(S.skin) || 0);
};

/* ---------- settings: the documented attributes ---------- */
const COLORS = ['#2dd4bf', '#ffffff', '#8a94a3', '#ffb74d', '#ff8a80', '#82b1ff', '#b388ff', '#a5d6a7'];
const enumRow = (label, hint, key, values) => {
  const row = document.createElement('div'); row.className = 'row';
  const lab = document.createElement('label'); lab.textContent = label;
  if (hint) {{ const s = document.createElement('small'); s.textContent = hint; lab.append(s); }}
  const sel = document.createElement('select');
  for (const v of values) {{
    const o = document.createElement('option'); o.value = v.value; o.textContent = v.text; sel.append(o);
  }}
  sel.value = String(S[key]); sel.onchange = () => {{ S[key] = sel.value; apply(); say(label + ': ' + sel.value); }};
  row.append(lab, sel); return row;
};
const numRow = (label, hint, key, min, max, step, fmt) => {
  const row = document.createElement('div'); row.className = 'row';
  const lab = document.createElement('label'); lab.textContent = label;
  if (hint) {{ const s = document.createElement('small'); s.textContent = hint; lab.append(s); }}
  const inp = document.createElement('input');
  inp.type = 'range'; inp.min = min; inp.max = max; inp.step = step; inp.value = S[key];
  const out = document.createElement('span'); out.style.cssText = 'min-width:52px;text-align:right;color:#8a94a3;font-size:12px';
  out.textContent = fmt ? fmt(S[key]) : S[key];
  inp.oninput = () => {{ S[key] = Number(inp.value); out.textContent = fmt ? fmt(S[key]) : S[key]; apply(); }};
  row.append(lab, inp, out); return row;
};
const boolRow = (label, hint, key) => {
  const row = document.createElement('div'); row.className = 'row';
  const lab = document.createElement('label'); lab.textContent = label;
  if (hint) {{ const s = document.createElement('small'); s.textContent = hint; lab.append(s); }}
  const wrap = document.createElement('div'); wrap.className = 'swi';
  for (const v of [true, false]) {{
    const b = document.createElement('button'); b.textContent = v ? 'on' : 'off';
    b.classList.toggle('on', !!S[key] === v);
    b.onclick = () => {{
      S[key] = v; apply();
      [...wrap.children].forEach((x) => x.classList.toggle('on', (x.textContent === 'on') === v));
      say(label + ': ' + (v ? 'on' : 'off'));
    }};
    wrap.append(b);
  }}
  row.append(lab, wrap); return row;
};

let formBuilt = false;
const buildSettings = () => {
  if (formBuilt) return; formBuilt = true;
  const frag = document.createDocumentFragment();

  const skinRow = document.createElement('div'); skinRow.className = 'row';
  const skinLab = document.createElement('label'); skinLab.textContent = 'Skin';
  const skinBtn = document.createElement('button');
  skinBtn.textContent = 'browse'; skinBtn.style.cssText = 'border:1px solid #2a303a;background:#171b21;color:#e8ecf1;border-radius:10px;height:30px;padding:0 12px;font-size:12px';
  skinBtn.onclick = () => {{ skinsEl.style.display = 'flex'; buildSkins(); mark(Number(S.skin) || 0); }};
  skinRow.append(skinLab, skinBtn);
  frag.append(skinRow);

  const colorRow = document.createElement('div'); colorRow.className = 'row';
  const colorLab = document.createElement('label'); colorLab.textContent = 'Colour';
  const sw = document.createElement('div'); sw.className = 'sw';
  for (const c of COLORS) {{
    const b = document.createElement('button'); b.style.background = c; b.title = c;
    b.classList.toggle('on', String(S.color).toLowerCase() === c);
    b.onclick = () => {{
      S.color = c; apply();
      [...sw.children].forEach((x) => x.classList.remove('on')); b.classList.add('on');
      say('colour ' + c);
    }};
    sw.append(b);
  }}
  colorRow.append(colorLab, sw);
  frag.append(colorRow);

  frag.append(numRow('Size', 'of the tile', 'size', 0.4, 1, 0.02, (v) => Math.round(v * 100) + '%'));
  frag.append(enumRow('Auto sleep', 'idle before the face sleeps', 'autoSleep', [
    {{ value: '0', text: 'never' }}, {{ value: '15000', text: '15 s' }}, {{ value: '45000', text: '45 s' }},
    {{ value: '120000', text: '2 min' }}, {{ value: '600000', text: '10 min' }}]));
  frag.append(enumRow('Wake on', '', 'wakeOn', [
    {{ value: 'activity', text: 'activity' }}, {{ value: 'interaction', text: 'touch' }}, {{ value: 'manual', text: 'manual' }}]));
  frag.append(enumRow('Motion', '', 'motion', [
    {{ value: 'auto', text: 'auto' }}, {{ value: 'reduce', text: 'reduced' }}, {{ value: 'full', text: 'full' }}]));
  frag.append(boolRow('Pointer follow', 'eyes follow the touch', 'pointerFollow'));
  frag.append(numRow('Head roundness', '', 'roundness', 0, 0.8, 0.02, (v) => Number(v).toFixed(2)));
  frag.append(boolRow('Press squeeze', 'press and hold the face', 'pressSqueeze'));
  frag.append(boolRow('Antenna drag', 'drag the antenna', 'antennaDrag'));

  formEl.append(frag);
};

document.getElementById('pick').onclick = () => {{ skinsEl.style.display = 'flex'; buildSkins(); mark(Number(S.skin) || 0); }};
document.getElementById('gear').onclick = () => {{ settingsEl.style.display = 'flex'; buildSettings(); }};
document.getElementById('skinsClose').onclick = () => { skinsEl.style.display = 'none'; };
document.getElementById('setClose').onclick = () => { settingsEl.style.display = 'none'; };

/* ---------- behaviour ---------- */
const setMode = (next) => {
  if (next === mode) return;
  const was = mode;
  mode = next;
  if (next === 'busy') a.startWaiting?.({{ variant: 'wrap' }});
  else if (next === 'wait') { a.play?.('wary'); nudge(true); }
  else if (was === 'busy') a.play?.('success');
  else if (was === 'wait') { nudge(false); a.play?.('affirm'); }
  else a.stopWaiting?.();
  updateMusicFace();
};

// a pending approval is easy to miss, so the face keeps looking over until it is answered
const NUDGE_MS = 8000;
let nudgeTimer = 0, nudgeFlip = false;
const nudge = (on) => {
  if (!on) { if (nudgeTimer) { clearInterval(nudgeTimer); nudgeTimer = 0; } return; }
  if (nudgeTimer) return;
  nudgeTimer = setInterval(() => {
    if (mode !== 'wait') { clearInterval(nudgeTimer); nudgeTimer = 0; return; }
    nudgeFlip = !nudgeFlip;
    a.play?.(nudgeFlip ? 'inspect' : 'wary');
  }, NUDGE_MS);
};

// BoopFace refuses press-squeeze for pointerType 'touch' (gestures.js:72), so a phone can never
// trigger it. When the setting is on, replay the touch as a synthetic mouse press at the same spot;
// the library's own gesture code then runs, animation included. Radius matches its own 0.32 test.
let squeezeWired = false;
const wireTouchSqueeze = () => {
  if (squeezeWired) return; squeezeWired = true;
  const fire = (type, e) => {
    const r = a.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const nx = (e.clientX - r.left) / r.width - .5, ny = (e.clientY - r.top) / r.height - .5;
    if (type === 'pointerdown' && nx * nx + ny * ny > 0.32 * 0.32) return;
    try {
      a.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true, pointerId: 999,
        pointerType: 'mouse', isPrimary: true, button: 0, buttons: type === 'pointerup' ? 0 : 1,
        clientX: e.clientX, clientY: e.clientY }));
    } catch (err) { console.warn('squeeze', err.message); }
  };
  a.addEventListener('pointerdown', (e) => { if (S.pressSqueeze && e.pointerType === 'touch') fire('pointerdown', e); });
  addEventListener('pointerup', (e) => { if (S.pressSqueeze) fire('pointerup', e); });
  addEventListener('pointercancel', (e) => { if (S.pressSqueeze) fire('pointercancel', e); });
};
wireTouchSqueeze();

apply();

try {
  phonebox.on('work', (w) => {
    const s = Array.isArray(w?.sessions) ? w.sessions : [];
    if (s.some((x) => x?.status === 'waiting')) setMode('wait');
    else if (s.some((x) => x?.status === 'busy')) setMode('busy');
    else setMode('idle');
  });

  // the DeepSeek balance is the one number this face is the face of: worry before it runs dry
  phonebox.on('push', (v) => {
    const d = v?.deepseek;
    if (!d) return;
    const n = parseFloat(String(d.value ?? '').replace(/[^0-9.]/g, ''));
    const next = !isFinite(n) ? '' : n < 0.10 ? 'err' : n < 1 ? 'warn' : '';
    if (next === balance) return;
    balance = next;
    if (alert || mode !== 'idle') return;
    a.play?.(worry());
  });

  // privacy: the microphone or the camera is in use. The camera is the louder signal and both
  // outrank the ambient media reaction, so "someone is recording" always wins the face.
  phonebox.on('state', (st) => {
    lastState = Date.now();
    if (!online) { online = true; a.play?.('success'); }
    const p = st?.privacy;
    const now = p ? (p.camera ? 'camera' : p.mic ? 'mic' : '') : '';
    if (now !== alert) {
      alert = now;
      if (now === 'camera') a.play?.('wary');
      else if (now === 'mic') a.play?.('inspect');
      else if (mode === 'idle') a.play?.(worry());
      updateMusicFace();
    }
    // the phone's own battery, which the app reports every 30 s into state.phone
    const ph = st?.phone;
    const bat = ph && typeof ph.level === 'number'
      ? (ph.plugged ? '' : ph.level < 10 ? 'err' : ph.level < 20 ? 'warn' : '') : '';
    if (ph && typeof ph.level === 'number') battLevel = ph.level;
    if (bat !== battery) {
      battery = bat;
      paintBattery();
      if (!alert && mode === 'idle') a.play?.(worry());
    }
    const mediaOn = !!st?.media?.playing;
    if (mediaOn !== playing) {
      if (eqEl) {
        eqEl.style.display = mediaOn ? 'flex' : 'none';
        if (mediaOn) [...eqEl.children].forEach((b) => {
          b.style.animation = 'none'; void b.offsetWidth; b.style.animation = '';
        });
      }
      if (auraEl) auraEl.style.display = mediaOn ? 'block' : 'none';
      document.body.classList.toggle('playing', mediaOn); // a sleeping face may still breathe
      if (playing !== null && mode === 'idle' && !alert && !slept) a.play?.(mediaOn ? 'success' : 'idle');
    }
    playing = mediaOn;
    updateMusicFace();

    // the bars follow the computer's output volume and grey out when muted: real signals,
    // not guessed audio levels
    if (eqEl) {
      const a = st?.audio;
      const vol = typeof a?.volume === 'number' ? a.volume : 60;
      document.body.style.setProperty('--amp', (0.45 + 0.55 * (vol / 100)).toFixed(2));
      eqEl.classList.toggle('muted', !!a?.muted);
    }
  });
}} catch (e) {{ console.warn(e); }}

// while music plays the face grooves with BoopFace's "waiting wave": the eyes bob up and
// down in turn, looping until playback stops or something more important takes the face
let musicFaceOn = false, touchUntil = 0, touchTimer = 0;
const TOUCH_PAUSE_MS = 20000;
const updateMusicFace = () => {
  const on = playing === true && mode === 'idle' && !alert && Date.now() >= touchUntil;
  if (on) {
    if (!musicFaceOn) { musicFaceOn = true; a.startWaiting?.({ variant: 'wave' }); }
  } else if (musicFaceOn) {
    musicFaceOn = false;
    // only take back an animation we own: busy/wait replaced it with their own waiting loop
    if (mode === 'idle') a.stopWaiting?.();
  }
};

// touching the face pauses the music groove: it wakes, plays normally, and only resumes
// the wave once you have left it alone for a while
const onFaceTouch = () => {
  touchUntil = Date.now() + TOUCH_PAUSE_MS;
  if (musicFaceOn) {
    musicFaceOn = false;
    a.stopWaiting?.();
    a.play?.('wake');
  }
  clearTimeout(touchTimer);
  touchTimer = setTimeout(() => { touchUntil = 0; updateMusicFace(); }, TOUCH_PAUSE_MS);
};
addEventListener('pointerdown', onFaceTouch, true);

// watchdog: the stream ticks every second, so 15 s of silence means the panel lost the agent
const WATCHDOG_MS = 15000;
lastState = Date.now();
setInterval(() => {
  if (!online || Date.now() - lastState <= WATCHDOG_MS) return;
  online = false;
  a.play?.('failure');
}, 5000);

// night: sleep with closed eyes instead of only dimming, and wake in the morning
const isNight = () => { const h = new Date().getHours(); return h >= 23 || h < 7; };
let slept = false;
const settle = () => {
  const n = isNight();
  if (n === slept) return;
  slept = n;
  if (n) a.play?.('sleep'); else a.play?.('wake');
};
settle();
setInterval(settle, 60000);

// a little life when nothing at all is happening, deliberately rare
let lastLife = Date.now();
setInterval(() => {
  if (slept || alert !== '' || mode !== 'idle') { lastLife = Date.now(); return; }
  if (Date.now() - lastLife < 12 * 60 * 1000) return;
  lastLife = Date.now();
  if (Math.random() < 0.6) a.play?.('bored');
}, 4 * 60 * 1000);
</script>
"""


def load_settings():
    cfg = dict(DEFAULTS)
    if SETTINGS.exists():
        try:
            cfg.update(json.loads(SETTINGS.read_text()))
        except Exception as exc:
            print("ignoring bad settings file:", exc)
    return cfg


def main():
    args = sys.argv[1:]
    cfg = load_settings()
    if args:
        if args[0] != "--set":
            raise SystemExit(__doc__)
        for pair in args[1:]:
            key, _, value = pair.partition("=")
            key = key.strip()
            if key not in DEFAULTS:
                raise SystemExit(f"unknown key: {key} (known: {', '.join(DEFAULTS)})")
            if isinstance(DEFAULTS[key], bool):
                cfg[key] = value.strip().lower() in ("1", "true", "on", "yes")
            elif isinstance(DEFAULTS[key], float):
                cfg[key] = float(value)
            elif isinstance(DEFAULTS[key], int):
                cfg[key] = int(value)
            elif key == "roundness":
                cfg[key] = None if value in ("none", "") else float(value)
            elif key == "skin":
                cfg[key] = None if value in ("none", "flat", "0", "") else int(value)
            else:
                cfg[key] = value
        SETTINGS.write_text(json.dumps(cfg, indent=2))

    bundle = BUNDLE.read_text(encoding="utf-8")
    if "</script" in bundle.lower():
        raise SystemExit("bundle contains </script")
    html = (TEMPLATE.replace("{{", "{").replace("}}", "}")
            .replace("{bundle}", bundle, 1).replace("{cfg}", json.dumps(cfg)))
    css = html.split("<style>")[1].split("</style>")[0]
    if css.count("{") != css.count("}"):
        raise SystemExit(f"refusing to install: stylesheet braces unbalanced "
                         f"({css.count('{')} open, {css.count('}')} close)")

    with urllib.request.urlopen(AGENT + "/api/settings", timeout=10) as r:
        version = r.headers.get("X-Config-Version")
        page_cfg = json.loads(r.read())
    page = next(p for p in page_cfg["pages"] if p["id"] == "boopface")
    page["widgets"][0]["options"]["html"] = html

    body = json.dumps(page_cfg, separators=(",", ":")).encode()
    req = urllib.request.Request(AGENT + "/api/settings", data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "X-Config-Version": version})
    with urllib.request.urlopen(req, timeout=60) as r:
        print("PUT ->", r.status, "| widget", len(html), "B | config", len(body), "B")
    print("settings:", json.dumps(cfg))


if __name__ == "__main__":
    main()
