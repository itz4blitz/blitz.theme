#!/usr/bin/env python3
"""Style presets and theme switching for the blitz.theme bar widget.

Two layers, both written for any user's setup:

1. Full Omarchy themes — `omarchy theme list` / `omarchy theme set <name>`.
2. Style presets on top of whatever theme is active. A preset writes
   ~/.config/omarchy/shell.toml, the live-watched machine override layer, so
   the bar and every dropdown restyle the moment the file lands. Preset colors
   are computed from the *current* theme's colors.toml (dimmed foregrounds,
   mixed surfaces) instead of hardcoded hexes, so the same preset looks right
   on Catppuccin and on Vantablack.

Usage:
  theme_collect.py state                    current theme + active preset + sliders
  theme_collect.py themes                   installable omarchy themes
  theme_collect.py set-theme <name>         omarchy theme set
  theme_collect.py presets                  built-in + user presets
  theme_collect.py apply <name>             write a preset to shell.toml
  theme_collect.py reset                    drop every key this tool owns
  theme_collect.py slide <key> <value>      one live control (bar-alpha,
                                            panel-alpha, font-size, text-dim)
  theme_collect.py save <name>              snapshot current overrides as a
                                            user preset (presets.json)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

HOME = Path.home()
STATE_THEME = HOME / ".local/state/omarchy/current/theme"
SHELL_TOML = HOME / ".config/omarchy/shell.toml"
STATE_FILE = Path(__file__).resolve().parent / "state.json"
USER_PRESETS = Path(__file__).resolve().parent / "presets.json"

# Everything this tool may write. Reset drops exactly these keys, never a key
# another tool (e.g. `omarchy display text size`) owns on its own.
OWNED_KEYS = {
    "bar.background", "bar.background-alpha", "bar.text", "bar.active",
    "popups.background", "popups.background-alpha", "popups.text",
    "popups.border", "popups.border-alpha",
    "menu.background", "menu.background-alpha", "menu.text",
    "menu.selected-text",
    "tooltip.background", "tooltip.background-alpha", "tooltip.text",
    "notifications.background", "notifications.background-alpha",
    "notifications.text",
    "controls.normal-border-width", "controls.selected-border-width",
    "font.base-size",
}

SLIDERS = {
    "bar-alpha": ("bar.background-alpha", 0.0, 1.0),
    "panel-alpha": ("popups.background-alpha", 0.0, 1.0),
    "font-size": ("font.base-size", 8, 24),
    "text-dim": ("__text_dim__", 0.0, 0.6),
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_hex(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(value or "").strip())
    if not match:
        return None
    text = match.group(1)
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % color


def hex_color(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    return parse_hex(value) or fallback


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    t = clamp(t, 0.0, 1.0)
    return rgb(tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def load_theme_palette() -> dict[str, tuple[int, int, int]]:
    palette: dict[str, tuple[int, int, int]] = {}
    try:
        data = tomllib.loads((STATE_THEME / "colors.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        data = {}
    for key in ("foreground", "background", "accent", "urgent", "muted", "green", "yellow"):
        raw = data.get(key)
        if isinstance(raw, str):
            parsed = parse_hex(raw)
            if parsed:
                palette[key] = parsed
    palette.setdefault("foreground", (0xAA, 0xAA, 0xAA))
    palette.setdefault("background", (0x11, 0x11, 0x11))
    palette.setdefault("accent", (0x88, 0x88, 0xCC))
    palette.setdefault("urgent", (0xCC, 0x66, 0x66))
    palette.setdefault("muted", (0x77, 0x77, 0x77))
    return palette


def dim(palette: dict, t: float) -> str:
    """Foreground mixed toward the background: 0 = full fg, 1 = bg."""
    return mix(palette["foreground"], palette["background"], clamp(t, 0.0, 1.0))


# Built-in presets. Values are either role names the shell resolves from the
# active theme (foreground/accent/background/urgent/muted/transparent) or
# computed strings. Nothing here is a theme-specific hex.
BUILTIN_PRESETS: dict[str, dict] = {
    "default": {
        "label": "Theme Default",
        "description": "Drop every override — exactly what the theme ships.",
        "keys": {},
    },
    "clear-glass": {
        "label": "Glass",
        "description": "Blurred clear bar, glassy panels — needs compositor blur.",
        "keys": {
            "bar.background": "background",
            "bar.background-alpha": 0.32,
            "bar.text": "__dim_0.06__",
            "bar.active": "urgent",
            "popups.background": "background",
            "popups.background-alpha": 0.55,
            "popups.text": "foreground",
            "popups.border": "accent",
            "popups.border-alpha": 0.35,
            "menu.background": "background",
            "menu.background-alpha": 0.55,
            "tooltip.background": "background",
            "tooltip.background-alpha": 0.8,
            "notifications.background": "background",
            "notifications.background-alpha": 0.72,
            "controls.normal-border-width": 1,
            "controls.selected-border-width": 0,
        },
    },
    "frost": {
        "label": "Frost",
        "description": "Half-there bar with glassy panels and accent edges.",
        "keys": {
            "bar.background": "background",
            "bar.background-alpha": 0.5,
            "bar.text": "__dim_0.04__",
            "bar.active": "urgent",
            "popups.background": "background",
            "popups.background-alpha": 0.68,
            "popups.text": "foreground",
            "popups.border": "accent",
            "popups.border-alpha": 0.5,
            "menu.background": "background",
            "menu.background-alpha": 0.68,
            "tooltip.background": "background",
            "tooltip.background-alpha": 0.85,
            "notifications.background": "background",
            "notifications.background-alpha": 0.8,
            "controls.normal-border-width": 1,
            "controls.selected-border-width": 1,
        },
    },
    "ink": {
        "label": "Ink",
        "description": "Opaque bar and panels — maximum contrast.",
        "keys": {
            "bar.background": "background",
            "bar.background-alpha": 1.0,
            "bar.text": "foreground",
            "bar.active": "urgent",
            "popups.background": "background",
            "popups.background-alpha": 1.0,
            "popups.text": "foreground",
            "popups.border": "accent",
            "popups.border-alpha": 1.0,
            "menu.background-alpha": 1.0,
            "tooltip.background-alpha": 1.0,
            "notifications.background-alpha": 1.0,
            "controls.normal-border-width": 1,
            "controls.selected-border-width": 1,
        },
    },
    "whisper": {
        "label": "Whisper",
        "description": "Barely-there blurred bar, whisper-dim text, clear panels.",
        "keys": {
            "bar.background": "background",
            "bar.background-alpha": 0.16,
            "bar.text": "__dim_0.24__",
            "bar.active": "urgent",
            "popups.background": "background",
            "popups.background-alpha": 0.62,
            "popups.text": "__dim_0.02__",
            "popups.border": "transparent",
            "popups.border-alpha": 0.0,
            "menu.background": "background",
            "menu.background-alpha": 0.62,
            "tooltip.background": "background",
            "tooltip.background-alpha": 0.78,
            "notifications.background": "background",
            "notifications.background-alpha": 0.7,
            "controls.normal-border-width": 0,
            "controls.selected-border-width": 0,
        },
    },
}


def load_user_presets() -> dict[str, dict]:
    try:
        raw = json.loads(USER_PRESETS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict] = {}
    for name, preset in raw.items():
        if isinstance(preset, dict) and isinstance(preset.get("keys"), dict):
            out[str(name)] = {
                "label": str(preset.get("label") or name),
                "description": str(preset.get("description") or "Saved preset"),
                "keys": {str(k): v for k, v in preset["keys"].items() if str(k) in OWNED_KEYS},
            }
    return out


def resolve_value(value, palette: dict) -> object:
    if not isinstance(value, str):
        return value  # numbers (alphas, sizes, widths) keep their TOML type
    dim_match = re.fullmatch(r"__dim_([0-9.]+)__", value)
    if dim_match:
        return dim(palette, float(dim_match.group(1)))
    return value


def read_shell_toml() -> dict[str, object]:
    try:
        data = tomllib.loads(SHELL_TOML.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    flat: dict[str, object] = {}
    for section, mapping in data.items():
        if not isinstance(mapping, dict):
            continue
        for key, value in mapping.items():
            flat[f"{section}.{key}"] = value
    return flat


def write_shell_toml(flat: dict[str, object]) -> None:
    tree: dict[str, dict[str, object]] = {}
    for full_key, value in flat.items():
        section, _, key = full_key.rpartition(".")
        tree.setdefault(section, {})[key] = value
    lines = [
        "# Written by blitz.theme (Omarchy shell style presets).",
        "# Hand edits are kept until the next preset apply or slider move.",
        "",
    ]
    for section in sorted(tree):
        lines.append(f"[{section}]")
        for key in sorted(tree[section]):
            value = tree[section][key]
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, (int, float)):
                rendered = str(value)
            else:
                rendered = json.dumps(str(value))
            lines.append(f"{key} = {rendered}")
        lines.append("")
    SHELL_TOML.parent.mkdir(parents=True, exist_ok=True)
    tmp = SHELL_TOML.with_suffix(".toml.tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(SHELL_TOML)


def load_state() -> dict:
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def current_overrides() -> dict[str, object]:
    return {k: v for k, v in read_shell_toml().items() if k in OWNED_KEYS}


def apply_preset(name: str) -> dict:
    presets = {**BUILTIN_PRESETS, **load_user_presets()}
    preset = presets.get(name)
    if preset is None:
        return {"ok": False, "error": "unknown-preset"}
    palette = load_theme_palette()
    flat = read_shell_toml()
    for key in OWNED_KEYS:
        flat.pop(key, None)
    for key, value in preset["keys"].items():
        if key not in OWNED_KEYS:
            continue
        flat[key] = resolve_value(value, palette)
    if preset["keys"].get("popups.text") is None and "popups.text" in flat:
        flat.pop("popups.text", None)
    write_shell_toml(flat)
    state = load_state()
    if name == "default":
        state.pop("preset", None)
    else:
        state["preset"] = name
    save_state(state)
    return {"ok": True, "applied": name}


def slide(key: str, raw_value: str) -> dict:
    if key not in SLIDERS:
        return {"ok": False, "error": "unknown-slider"}
    toml_key, low, high = SLIDERS[key]
    try:
        value = clamp(float(raw_value), low, high)
    except ValueError:
        return {"ok": False, "error": "bad-value"}
    palette = load_theme_palette()
    flat = read_shell_toml()
    if toml_key == "__text_dim__":
        flat["bar.text"] = dim(palette, value / 2.0 if value <= 1.0 else value / 100.0)
    else:
        flat[toml_key] = int(value) if key == "font-size" else round(value, 3)
    write_shell_toml(flat)
    state = load_state()
    state.setdefault("sliders", {})[key] = int(value) if key == "font-size" else round(value, 3)
    save_state(state)
    return {"ok": True, "key": key, "value": value}


def save_preset(name: str) -> dict:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(name or "").strip()).strip("-").lower()
    if not cleaned or cleaned in BUILTIN_PRESETS:
        return {"ok": False, "error": "bad-name"}
    overrides = current_overrides()
    palette = load_theme_palette()
    presets = load_user_presets()
    presets[cleaned] = {
        "label": str(name).strip() or cleaned,
        "description": "Saved from the current look.",
        # Store resolved hexes: a snapshot should reproduce what you saw even
        # after the theme's palette shifts underneath it.
        "keys": {k: (v if not isinstance(v, str) else v) for k, v in overrides.items()},
    }
    USER_PRESETS.write_text(json.dumps(presets, indent=2, sort_keys=True), encoding="utf-8")
    state = load_state()
    state["preset"] = cleaned
    save_state(state)
    return {"ok": True, "saved": cleaned}


def list_themes() -> list[str]:
    try:
        raw = subprocess.check_output(["omarchy", "theme", "list"], text=True, timeout=5)
    except Exception:
        return []
    return [line.strip() for line in raw.splitlines() if line.strip()]


def current_theme() -> str:
    try:
        raw = subprocess.check_output(["omarchy", "theme", "current"], text=True, timeout=5)
    except Exception:
        return ""
    return raw.strip().splitlines()[0] if raw.strip() else ""


def set_theme(name: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .-]*", str(name or "")):
        return {"ok": False, "error": "bad-name"}
    try:
        subprocess.check_call(["omarchy", "theme", "set", name], timeout=120)
    except Exception:
        return {"ok": False, "error": "set-failed"}
    # A new theme regenerates shell.toml from its own templates; re-apply the
    # active preset so the chosen style survives the theme switch.
    state = load_state()
    if state.get("preset") and state["preset"] != "default":
        apply_preset(str(state["preset"]))
    return {"ok": True, "theme": name}


def emit_state() -> dict:
    state = load_state()
    return {
        "ok": True,
        "theme": current_theme(),
        "themes": list_themes(),
        "preset": state.get("preset", "default"),
        "sliders": state.get("sliders", {}),
        "builtinPresets": [
            {"id": pid, "label": p["label"], "description": p["description"]}
            for pid, p in BUILTIN_PRESETS.items()
        ],
        "userPresets": [
            {"id": pid, "label": p["label"], "description": p["description"]}
            for pid, p in load_user_presets().items()
        ],
        "overrides": current_overrides(),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] == "state":
        print(json.dumps(emit_state()))
        return 0
    command, rest = args[0], args[1:]
    if command == "themes":
        print(json.dumps({"ok": True, "themes": list_themes()}))
    elif command == "set-theme" and len(rest) == 1:
        print(json.dumps(set_theme(rest[0])))
    elif command == "presets":
        print(json.dumps({"ok": True, "builtin": list(BUILTIN_PRESETS), "user": list(load_user_presets())}))
    elif command == "apply" and len(rest) == 1:
        print(json.dumps(apply_preset(rest[0])))
    elif command == "reset":
        print(json.dumps(apply_preset("default")))
    elif command == "slide" and len(rest) == 2:
        print(json.dumps(slide(rest[0], rest[1])))
    elif command == "save" and len(rest) == 1:
        print(json.dumps(save_preset(rest[0])))
    else:
        print(json.dumps({"ok": False, "error": "usage"}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
