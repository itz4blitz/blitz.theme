"""blitz.theme collector tests — portable, no real config is touched."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme_collect as tc


class ColorMathTest(unittest.TestCase):
    def test_mix_interpolates_and_clamps(self) -> None:
        self.assertEqual(tc.mix((0, 0, 0), (255, 255, 255), 0.0), "#000000")
        self.assertEqual(tc.mix((0, 0, 0), (255, 255, 255), 1.0), "#ffffff")
        mid = tc.mix((0, 0, 0), (200, 100, 50), 0.5)
        self.assertEqual(mid, "#643219")
        self.assertEqual(tc.mix((10, 10, 10), (20, 20, 20), 9.0), "#141414")

    def test_parse_hex_accepts_bare_and_hash_forms(self) -> None:
        self.assertEqual(tc.parse_hex("#1a2b3c"), (0x1A, 0x2B, 0x3C))
        self.assertEqual(tc.parse_hex("1a2b3c"), (0x1A, 0x2B, 0x3C))
        self.assertIsNone(tc.parse_hex("nope"))
        self.assertIsNone(tc.parse_hex("#12345"))


class PresetsTest(unittest.TestCase):
    def test_builtin_presets_only_own_allowed_keys(self) -> None:
        for name, preset in tc.BUILTIN_PRESETS.items():
            for key in preset["keys"]:
                self.assertIn(key, tc.OWNED_KEYS, f"{name} writes foreign key {key}")

    def test_default_preset_is_empty_and_clears_everything(self) -> None:
        self.assertEqual(tc.BUILTIN_PRESETS["default"]["keys"], {})


class TomlRoundTripTest(unittest.TestCase):
    def test_write_and_read_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tc.SHELL_TOML = Path(tmp) / "shell.toml"
            tc.write_shell_toml(
                {
                    "bar.background-alpha": 0.55,
                    "bar.text": "#aabbcc",
                    "font.base-size": 14,
                    "popups.border": "accent",
                }
            )
            flat = tc.read_shell_toml()
        self.assertEqual(flat["bar.background-alpha"], 0.55)
        self.assertEqual(flat["bar.text"], "#aabbcc")
        self.assertEqual(flat["font.base-size"], 14)
        self.assertEqual(flat["popups.border"], "accent")


class ApplyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tc.SHELL_TOML = Path(self._tmp.name) / "shell.toml"
        tc.STATE_FILE = Path(self._tmp.name) / "state.json"
        tc.USER_PRESETS = Path(self._tmp.name) / "presets.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_apply_clears_previous_owned_keys_keeps_foreign(self) -> None:
        tc.write_shell_toml({"bar.text": "#111111", "bar.background-alpha": 1.0, "other.tool": "keep"})
        result = tc.apply_preset("clear-glass")
        self.assertTrue(result["ok"])
        flat = tc.read_shell_toml()
        self.assertEqual(flat["bar.background-alpha"], 0.32)
        # The preset re-sets bar.text to a dimmed hex computed from the palette.
        self.assertIn("bar.text", flat)
        self.assertEqual(flat["other.tool"], "keep")  # never touches keys it does not own
        state = json.loads(tc.STATE_FILE.read_text())
        self.assertEqual(state["preset"], "clear-glass")

    def test_apply_default_drops_owned_keys_only(self) -> None:
        tc.write_shell_toml({"bar.background-alpha": 0.2, "font.base-size": 20, "other.tool": "keep"})
        tc.apply_preset("clear-glass")
        result = tc.apply_preset("default")
        self.assertTrue(result["ok"])
        flat = tc.read_shell_toml()
        self.assertNotIn("bar.background-alpha", flat)
        self.assertNotIn("font.base-size", flat)
        self.assertEqual(flat["other.tool"], "keep")
        state = json.loads(tc.STATE_FILE.read_text())
        self.assertNotIn("preset", state)

    def test_apply_unknown_preset_fails(self) -> None:
        self.assertFalse(tc.apply_preset("nope")["ok"])

    def test_dim_marker_resolves_against_current_theme(self) -> None:
        tc.write_shell_toml({})
        with unittest.mock.patch.object(tc, "load_theme_palette", return_value={
            "foreground": (255, 255, 255), "background": (0, 0, 0), "accent": (128, 128, 255),
            "urgent": (255, 0, 0), "muted": (128, 128, 128),
        }):
            tc.apply_preset("clear-glass")
        flat = tc.read_shell_toml()
        # dim 0.06 of white on black: 255 * 0.94 = 239.7 ≈ #f0
        self.assertEqual(flat["bar.text"].lower(), "#f0f0f0")
        self.assertEqual(flat["bar.background"], "background")

    def test_role_values_pass_through_unresolved(self) -> None:
        with unittest.mock.patch.object(tc, "load_theme_palette", return_value={
            "foreground": (255, 255, 255), "background": (0, 0, 0), "accent": (1, 2, 3),
            "urgent": (4, 5, 6), "muted": (7, 8, 9),
        }):
            tc.apply_preset("ink")
        flat = tc.read_shell_toml()
        self.assertEqual(flat["popups.border"], "accent")  # shell resolves roles
        self.assertEqual(flat["bar.text"], "foreground")


class SliderTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tc.SHELL_TOML = Path(self._tmp.name) / "shell.toml"
        tc.STATE_FILE = Path(self._tmp.name) / "state.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_slider_writes_key_and_state(self) -> None:
        result = tc.slide("bar-alpha", "0.35")
        self.assertTrue(result["ok"])
        self.assertEqual(tc.read_shell_toml()["bar.background-alpha"], 0.35)
        state = json.loads(tc.STATE_FILE.read_text())
        self.assertEqual(state["sliders"]["bar-alpha"], 0.35)

    def test_font_size_is_integer_and_clamped(self) -> None:
        self.assertTrue(tc.slide("font-size", "41")["ok"])
        flat = tc.read_shell_toml()
        self.assertEqual(flat["font.base-size"], 24)  # clamped high
        self.assertIsInstance(flat["font.base-size"], int)

    def test_text_dim_writes_dimmed_hex(self) -> None:
        with unittest.mock.patch.object(tc, "load_theme_palette", return_value={
            "foreground": (200, 200, 200), "background": (0, 0, 0), "accent": (1, 1, 1),
            "urgent": (2, 2, 2), "muted": (3, 3, 3),
        }):
            result = tc.slide("text-dim", "0.4")
        self.assertTrue(result["ok"])
        self.assertTrue(tc.read_shell_toml()["bar.text"].startswith("#"))

    def test_unknown_slider_fails(self) -> None:
        self.assertFalse(tc.slide("nope", "1")["ok"])
        self.assertFalse(tc.slide("bar-alpha", "banana")["ok"])


class SavePresetTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tc.SHELL_TOML = Path(self._tmp.name) / "shell.toml"
        tc.STATE_FILE = Path(self._tmp.name) / "state.json"
        tc.USER_PRESETS = Path(self._tmp.name) / "presets.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_save_snapshots_overrides_and_rejects_collisions(self) -> None:
        tc.write_shell_toml({"bar.background-alpha": 0.4, "font.base-size": 13, "other.tool": "x"})
        result = tc.save_preset("My Look!!")
        self.assertTrue(result["ok"])
        self.assertEqual(result["saved"], "my-look")
        saved = json.loads(tc.USER_PRESETS.read_text())["my-look"]
        self.assertEqual(saved["keys"]["bar.background-alpha"], 0.4)
        self.assertNotIn("other.tool", saved["keys"])  # snapshot only what we own
        self.assertFalse(tc.save_preset("default")["ok"])  # cannot shadow builtin
        self.assertFalse(tc.save_preset("   ")["ok"])


if __name__ == "__main__":
    unittest.main()
