import tempfile
import unittest
from pathlib import Path

from briefing.build import build
from briefing.config import load_config
from briefing.gather import Article
from briefing.rank import rank


class MorningBriefingPipelineTests(unittest.TestCase):
    def test_demo_build_produces_html_with_required_sections(self) -> None:
        html = build(demo=True)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Morning AI Brief", html)
        self.assertIn("Top signals", html)
        self.assertIn("Issue metadata", html)
        self.assertIn("Story treatment", html)
        self.assertIn("Read next", html)

    def test_rank_includes_category_annotations(self) -> None:
        config = load_config(Path("config.yaml"))
        articles = [
            Article(
                title="Hermes agents get better tool memory",
                url="https://example.com/hermes-memory",
                source="Example",
                description="Hermes agents improve tool reliability and memory behavior.",
                content_text="Hermes memory tool use reliability browser workflows",
                date="2026-06-03T10:00:00+00:00",
            ),
            Article(
                title="General AI roundup",
                url="https://example.com/general-roundup",
                source="Example",
                description="A broad recap of AI headlines.",
                content_text="Benchmarks and model updates across the market",
                date="2026-05-20T10:00:00+00:00",
            ),
        ]

        ranked = rank(articles, config, momentum={"hermetic_agents": 1.0})

        self.assertEqual(ranked[0].category, "hermetic_agents")
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_render_writes_to_disk_cleanly(self) -> None:
        html = build(demo=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "brief.html"
            output_path.write_text(html, encoding="utf-8")
            written = output_path.read_text(encoding="utf-8")

        self.assertIn("footrail", written)


if __name__ == "__main__":
    unittest.main()
