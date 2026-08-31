import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update-buildroot.py"
spec = importlib.util.spec_from_file_location("update_buildroot", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class BuildrootUpdaterTests(unittest.TestCase):
    def test_stable_row_wins_over_candidate(self):
        html = """
        <table>
          <tr><th></th><th>Series</th><th>Latest release</th></tr>
          <tr><td>Candidate</td><td>2026.08.x</td><td>2026.08-rc3</td></tr>
          <tr><td>Stable</td><td>2026.05.x</td><td>2026.05.2</td></tr>
          <tr><td>Long-term support</td><td>2025.02.x</td><td>2025.02.17</td></tr>
        </table>
        """
        self.assertEqual(mod.stable_version(html), "2026.05.2")

    def test_series_classification(self):
        self.assertTrue(mod.same_series("2026.05.1", "2026.05.2"))
        self.assertFalse(mod.same_series("2026.05.2", "2026.08"))

    def test_signed_sha256_parser(self):
        text = """
SHA1: deadbeef buildroot-2026.05.2.tar.xz
SHA256: 7cd0b79e657b8a1760cef0a68d083265726efe96a17f7f0cb9c10dd6d29b7107 buildroot-2026.05.2.tar.xz
"""
        self.assertEqual(
            mod.parse_signed_sha256(text, "buildroot-2026.05.2.tar.xz"),
            "7cd0b79e657b8a1760cef0a68d083265726efe96a17f7f0cb9c10dd6d29b7107",
        )

    def test_trusted_signer_format(self):
        signers = mod.trusted_signers()
        self.assertIn("18C7DF2819C1733D822D599EA500D6EE9CB0E540", signers)
        self.assertIn("AB07D806D2CE741FB886EE50B025BA8B59C36319", signers)


if __name__ == "__main__":
    unittest.main()
