# blitz.theme

Style presets and theme switching for the Omarchy shell — one chip that
restyles the bar **and every dropdown panel** at once, live, for any theme
and any user.

```bash
omarchy plugin add https://github.com/itz4blitz/blitz.theme.git --enable
omarchy plugin update blitz.theme
```

## How it works

The shell already watches `~/.config/omarchy/shell.toml` — a machine-level
override layer that sits on top of whatever theme is active. Presets write
keys there (`[bar]`, `[popups]`, `[menu]`, `[tooltip]`, `[notifications]`,
`[controls]`, `[font]`), so the change lands instantly with no restart, and
every bar widget and panel picks it up because they all consume the same
Color/Style singletons.

- **Presets** — *Theme Default*, *Clear Glass* (invisible bar, softened
  text), *Frost*, *Ink*, *Whisper*. Colors are computed from the current
  theme's palette (`foreground`, `accent`, …) instead of hardcoded hexes,
  so the same preset looks right on Catppuccin and on Vantablack.
- **Live sliders** — bar opacity, panel opacity, bar text dim, font size.
  Each move writes one key; effects are immediate.
- **Save** — name the current combination and it lands in `presets.json`
  (gitignored user config) as your own preset.
- **Omarchy theme switcher** — the same dropdown also runs
  `omarchy theme set`, and your active preset is re-applied on top after
  the switch.

`state.json` (also gitignored) remembers the active preset and slider
values. Nothing about any specific theme, monitor, or account is baked in.

## Files

- `theme_collect.py` — everything the chip does: state, presets, sliders,
  theme list/set. JSON in, JSON out.
- `BarWidget.qml` — the chip and panel.

## Test

```bash
python3 -m unittest discover -s . -p 'test_*.py'
```
