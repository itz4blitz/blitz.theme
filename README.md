# blitz.theme

Style presets and theme switching for the Omarchy shell — one chip that
restyles the bar **and every dropdown panel** at once, live, for any theme
and any user.

```bash
omarchy plugin add https://github.com/itz4blitz/blitz.theme.git --enable
omarchy plugin update blitz.theme
```

## Prerequisite: compositor blur (one time)

The glass presets are translucency **plus compositor blur**; without blur,
transparency is just noise. Enable Hyprland blur and layer rules for the
shell surfaces in `~/.config/hypr/looknfeel.lua` (snake_case field names —
the Lua binding rejects `ignorealpha`):

```lua
hl.config({
  decoration = {
    blur = {
      enabled = true,
      size = 7,
      passes = 3,
      contrast = 1.05,
      vibrancy = 0.17,
      noise = 0.02,
    },
  },
})

-- Layer-shell surfaces only blur when a rule says so.
hl.layer_rule({ match = { namespace = "omarchy-bar" }, blur = true, ignore_alpha = 0.0 })
hl.layer_rule({ match = { namespace = "omarchy-keyboard-panel" }, blur = true, ignore_alpha = 0.0 })
hl.layer_rule({ match = { namespace = "omarchy-menu" }, blur = true, ignore_alpha = 0.0 })
```

Then `hyprctl reload`. Regular windows (including plugin FloatingWindows)
blur automatically once global blur is on. Verify with
`hyprctl configerrors` — it must be empty.

## How it works

The shell already watches `~/.config/omarchy/shell.toml` — a machine-level
override layer that sits on top of whatever theme is active. Presets write
keys there (`[bar]`, `[popups]`, `[menu]`, `[tooltip]`, `[notifications]`,
`[controls]`, `[font]`), so the change lands instantly with no restart, and
every bar widget and panel picks it up because they all consume the same
Color/Style singletons.

- **Presets** — *Theme Default*, *Glass* (blurred clear bar, glassy panels),
  *Frost*, *Ink*, *Whisper*. Colors are computed from the current theme's
  palette (`foreground`, `accent`, …) instead of hardcoded hexes, so the same
  preset looks right on Catppuccin and on Vantablack.
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
