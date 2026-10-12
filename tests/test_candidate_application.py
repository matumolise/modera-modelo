"""Ensayos reales de Git sobre repos temporales: aislamiento e integridad."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.validation.candidate_application import DeliverySpec, prepare_candidate


class CandidateApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.destination = self.root / "repo", self.root / "candidate"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "base.txt").write_bytes(b"base\n")
        self.git("add", "base.txt")
        self.git("commit", "-qm", "Fixture base")
        self.base = self.git("rev-parse", "HEAD")
        protected = {"protected-" + str(n): self.base for n in range(5)}
        for name in protected:
            self.git("branch", name, self.base)
        self.git("remote", "add", "origin", "https://github.com/matumolise/modera-modelo.git")
        (self.repo / "base.txt").write_bytes(b"candidate\n")
        self.patch = self.root / "candidate.patch"
        self.patch.write_bytes(self.command("diff", "--binary", "--full-index").stdout)
        self.blob = self.git("hash-object", "base.txt")
        (self.repo / "base.txt").write_bytes(b"original uncommitted work\n")
        (self.repo / "untracked.txt").write_bytes(b"keep\n")
        self.spec = DeliverySpec(self.base, "protected-0", protected,
                                 sha256(self.patch.read_bytes()).hexdigest(), {"base.txt": self.blob})

    def command(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def git(self, *args):
        return self.command(*args).stdout.decode().strip()

    def prepare(self, **kwargs):
        return prepare_candidate(self.repo, self.destination, self.patch, "new-candidate",
                                 kwargs.get("spec", self.spec), fetch_base=False)

    def test_applies_to_base_preserving_dirty_original_and_five_refs(self):
        report = self.prepare()
        self.assertEqual(report["status"], "PREPARED_ONLY")
        self.assertEqual((self.destination / "base.txt").read_bytes(), b"candidate\n")
        self.assertEqual((self.repo / "base.txt").read_bytes(), b"original uncommitted work\n")
        self.assertEqual((self.repo / "untracked.txt").read_bytes(), b"keep\n")
        for name, value in self.spec.protected_refs.items():
            self.assertEqual(self.git("rev-parse", name), value)
        self.assertEqual(self.git("rev-parse", "new-candidate"), self.base)

    def test_tampered_patch_stops_before_creating_branch_or_destination(self):
        self.patch.write_bytes(self.patch.read_bytes() + b"changed")
        with self.assertRaisesRegex(RuntimeError, "Huella"):
            self.prepare()
        self.assertFalse(self.destination.exists())
        self.assertNotIn("new-candidate", self.git("branch", "--format=%(refname:short)").splitlines())

    def test_autocrlf_setting_is_preserved_while_candidate_bytes_are_exact(self):
        self.git("config", "core.autocrlf", "true")
        self.prepare()
        self.assertEqual((self.destination / "base.txt").read_bytes(), b"candidate\n")
        self.assertEqual(self.git("config", "core.autocrlf"), "true")
        self.assertEqual((self.repo / "base.txt").read_bytes(), b"original uncommitted work\n")

    def test_changed_protected_ref_stops_before_creating_destination(self):
        (self.repo / "base.txt").write_bytes(b"different commit\n")
        self.git("add", "base.txt")
        self.git("commit", "-qm", "Fixture external change")
        self.git("branch", "-f", "protected-4", "HEAD")
        with self.assertRaisesRegex(RuntimeError, "protegida"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_preserved(self):
        self.destination.mkdir()
        existing = self.destination / "keep.txt"
        existing.write_bytes(b"existing")
        with self.assertRaisesRegex(RuntimeError, "destino ya existe"):
            self.prepare()
        self.assertEqual(existing.read_bytes(), b"existing")

    def test_existing_branch_is_preserved(self):
        self.git("branch", "new-candidate", self.base)
        with self.assertRaisesRegex(RuntimeError, "rama destino ya existe"):
            self.prepare()
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.git("rev-parse", "new-candidate"), self.base)

    def test_wrong_applied_inventory_fails_without_altering_original(self):
        bad = replace(self.spec, changed_blobs={"base.txt": "0" * 40})
        with self.assertRaisesRegex(RuntimeError, "Archivo aplicado no coincide"):
            self.prepare(spec=bad)
        self.assertEqual((self.repo / "base.txt").read_bytes(), b"original uncommitted work\n")
        self.assertEqual(self.git("rev-parse", "protected-0"), self.base)


if __name__ == "__main__":
    unittest.main()
