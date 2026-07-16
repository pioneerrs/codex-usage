import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LineEndingTests(unittest.TestCase):
    def test_wsl_launchers_are_lf_and_attributes_enforce_it(self):
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.sh text eol=lf", attributes)
        self.assertIn("codex-usage text eol=lf", attributes)
        for relative in (
            "run.sh",
            "codex-usage",
            "scripts/bootstrap.sh",
            "scripts/check.sh",
            "scripts/demo.sh",
        ):
            with self.subTest(path=relative):
                self.assertNotIn(b"\r\n", (ROOT / relative).read_bytes())


if __name__ == "__main__":
    unittest.main()
