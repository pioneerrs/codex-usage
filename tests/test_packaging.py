import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")


@unittest.skipUnless(importlib.util.find_spec("setuptools"), "requires the setuptools build backend")
class PackagingTests(unittest.TestCase):
    def test_build_metadata_with_generated_reports_excludes_local_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("pyproject.toml", "README.md", "LICENSE"):
                shutil.copy2(ROOT / name, root / name)
            shutil.copytree(ROOT / "codex_usage", root / "codex_usage", ignore=shutil.ignore_patterns("__pycache__"))
            for name in ("output", ".codex-usage", ".workbuddy"):
                (root / name).mkdir()
                (root / name / "private-report.html").write_text("private fixture", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-c", "from setuptools.build_meta import get_requires_for_build_wheel; get_requires_for_build_wheel()"],
                cwd=root,
                capture_output=True,
                text=True,
                errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metadata = next(root.glob("*.egg-info"))
            self.assertEqual((metadata / "top_level.txt").read_text().splitlines(), ["codex_usage"])
            self.assertNotIn("private-report.html", (metadata / "SOURCES.txt").read_text())


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL, "requires Windows PowerShell")
class BootstrapTests(unittest.TestCase):
    def test_failed_install_stops_bootstrap_without_success_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            script = root / "scripts" / "bootstrap.ps1"
            shutil.copy2(ROOT / "scripts" / "bootstrap.ps1", script)
            subprocess.run(
                [sys.executable, "-m", "venv", "--without-pip", str(root / ".venv")],
                check=True,
                capture_output=True,
            )
            # Exercise real native exit codes without depending on a network failure.
            (root / "pip.py").write_text(
                "import sys\nsys.exit(0 if '--upgrade' in sys.argv else 23)\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                capture_output=True,
                text=True,
                errors="replace",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Package installation failed", result.stderr)
            self.assertNotIn("Bootstrap complete", result.stdout)


if __name__ == "__main__":
    unittest.main()
