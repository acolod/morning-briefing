import tempfile
import unittest
from pathlib import Path

from briefing.build import _DEMO_EDITORIAL, build


class MorningBriefingPipelineTests(unittest.TestCase):
    def test_demo_build_produces_html_with_required_sections(self) -> None:
        html = build(demo=True)

        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Morning AI Brief", html)
        self.assertIn("Top story", html)
        self.assertIn("Signals", html)
        self.assertIn("Radar", html)
        self.assertIn("One move today", html)
        self.assertIn("Issue metadata", html)

    def test_editorial_dict_build_uses_source_payload(self) -> None:
        editorial = dict(_DEMO_EDITORIAL)
        editorial["one_move"] = "Open the dynamic discovery spec and compare it to the current tool registry."

        html = build(editorial=editorial)

        self.assertIn("Open the dynamic discovery spec", html)

    def test_render_writes_to_disk_cleanly(self) -> None:
        html = build(demo=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "brief.html"
            output_path.write_text(html, encoding="utf-8")
            written = output_path.read_text(encoding="utf-8")

        self.assertIn("footrail", written)


if __name__ == "__main__":
    unittest.main()
