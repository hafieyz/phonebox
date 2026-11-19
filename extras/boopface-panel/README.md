# BoopFace panel page + DeepSeek balance

Two additions to PhoneBox, built and tested on Linux Mint 22.3 / X11 with a realme RMX2170
(Android 12) as the desk panel.

## boopface/

A panel page that is just an animated face — [BoopFace](https://github.com/CX-ArtLab/BoopFace) (MIT)
inside an `html` widget. The library is bundled to one IIFE and inlined, so the panel needs no
network and no CDN; `bundle.sh` regenerates it from the published npm package.

```bash
python3 boopface/build.py                                     # install with saved settings
python3 boopface/build.py --set skin=305 --set motion=reduce  # change a documented option
```

The gear sheet on the phone exposes the library's own options — `skin`, `color`, `auto-sleep`,
`wake-on`, `motion`, `press-squeeze`, `antenna-drag`, plus `setPointerFollow()` and
`setHeadRoundness()`. A sandboxed iframe has no storage, so a change made on the phone only lives
until the panel reloads; `--set` bakes it in permanently.

BoopFace refuses `press-squeeze` for `pointerType === 'touch'` (it is a mouse gesture), so on a
touchscreen the gesture needs a synthetic mouse event, which `build.py` sends when the option is on.

### What the face reacts to

| Signal | Face |
|---|---|
| Agent session `busy` / `waiting` | waiting animation / `wary`, with a nudge every 8 s while an approval is pending |
| Microphone or camera in use | `inspect` / `wary` |
| DeepSeek balance under $1 / $0.10 | `wary` / `failure` |
| Phone battery under 20 % / 10 %, unplugged | `wary` / `failure`, plus a battery glyph above the head |
| 23:00–07:00 | sleeps, dimmed |
| Idle 12+ minutes | occasional `bored` glance |
| Agent stream silent 15 s | `failure`, `success` when it returns |

### Music

While the panel reports playback it shows an equalizer (12 bars), a 3 % bob at 120 BPM and a
conic aura rotating around the head; the face runs BoopFace's `startWaiting({variant:'wave'})`
groove. Touching the face pauses the groove for 20 s.

None of it follows the actual audio: an `html` widget receives `playing`, `volume` and `muted`
only — no levels and no spectrum — so every animation runs on a fixed 125 ms beat grid. Real
per-band reaction would need the app to forward `spectrum` frames to widgets.

## ai-quota/

DeepSeek has no usage/quota endpoint, only `GET /user/balance`, so the quota card is a pushed value:

```bash
DEEPSEEK_API_KEY=sk-... python3 ai-quota/deepseek-balance.py
```

The key is read from `$DEEPSEEK_API_KEY` first, then from `~/.dsh/.credentials.yaml`. It never
reaches the panel, the config or this repository — only the balance is pushed.

```bash
cp ai-quota/phonebox-deepseek.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now phonebox-deepseek.timer
```

## Browser artwork

This branch also carries two agent changes: `Unix/MediaMonitor.cs` accepts extension-less `file://`
artwork (Chromium publishes the media-session image as `/tmp/.org.chromium.Chromium.XXXXXX`, which
the old extension allowlist always dropped), and `/api/state` now exposes the phone's own battery as
`phone: {level, plugged}`, which the panel already reports to `/api/phone/battery`.

## Security

No credentials are in this folder:

- The agent's `config.json` (which holds `lan.token`, `lan.webhookToken` and the pinned TLS key) is
  machine state, never committed.
- The DeepSeek key is read at runtime; there is no key literal in any script here.

## Credits

- [PhoneBox](https://github.com/ersinkoc/phonebox) — MIT, by Ersin Koç.
- [BoopFace](https://github.com/CX-ArtLab/BoopFace) — MIT, by CX ArtLab; `boopface.iife.js` is a
  minified bundle of that library.
