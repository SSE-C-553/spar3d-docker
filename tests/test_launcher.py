import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import launcher


FAKE_UPSTREAM = '''
import argparse
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("images", nargs="+")
parser.add_argument("--output-dir", required=True)
parser.add_argument("--device", required=True)
parser.add_argument("--batch_size", required=True)
parser.add_argument("--texture-resolution", required=True)
parser.add_argument("--remesh_option", required=True)
parser.add_argument("--reduction_count_type", required=True)
parser.add_argument("--low-vram-mode", action="store_true")
args = parser.parse_args()
assert args.device == "cuda"
assert args.reduction_count_type == "keep"
assert "HUGGING_FACE_HUB_TOKEN" not in os.environ
assert "SPAR3D_USE_CPU" not in os.environ
assert "SPAR3D_LOW_VRAM" not in os.environ
print("upstream accidentally logged " + os.environ["HF_TOKEN"])
for index, image in enumerate(args.images):
    target = Path(args.output_dir) / str(index)
    target.mkdir()
    (target / "mesh.glb").write_text(image, encoding="utf-8")
    (target / "points.ply").write_text("points", encoding="utf-8")
    if os.environ.get("FAKE_FAIL"):
        sys.exit(7)
'''


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inputs = self.root / "input"
        self.inputs.mkdir()
        self.outputs = self.root / "output"
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        (self.upstream / "run.py").write_text(FAKE_UPSTREAM, encoding="utf-8")
        self.secret = self.root / "token"
        self.token = "hf_synthetic_test_credential_never_real"
        self.secret.write_text(self.token + "\n", encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {
            "UPSTREAM_DIR": str(self.upstream), "HF_TOKEN_FILE": str(self.secret),
            "HUGGING_FACE_HUB_TOKEN": "unrelated-inherited-token",
            "SPAR3D_USE_CPU": "1", "SPAR3D_LOW_VRAM": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def image(self, name):
        path = self.inputs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture image: upstream is mocked")
        return path

    def run_cli(self, *args):
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            return launcher.main(list(args))

    def infer(self, *args):
        return self.run_cli("infer", "--input-dir", str(self.inputs), "--output-dir", str(self.outputs), *args)

    def manifest(self):
        runs = list(self.outputs.iterdir())
        self.assertEqual(len(runs), 1)
        return runs[0], json.loads((runs[0] / "manifest.json").read_text(encoding="utf-8"))

    def test_scan_is_sorted_case_insensitive_and_nonrecursive(self):
        upper = self.image("Zoo.JPEG")
        lower = self.image("ant.png")
        self.image("ignored.webp")
        self.image("nested/other.jpg")
        self.assertEqual(launcher.collect_images([], self.inputs), [lower, upper])

    def test_explicit_images_are_validated_and_sorted(self):
        second = self.image("b.JPG")
        first = self.image("a.png")
        self.assertEqual(launcher.collect_images([str(second), str(first)], "unused"), [first, second])
        for invalid in (self.inputs, self.inputs / "missing.png", self.image("invalid.gif")):
            with self.subTest(invalid=invalid), self.assertRaises(launcher.LauncherError):
                launcher.collect_images([str(invalid)], "unused")

    def test_empty_or_missing_directory_fails_before_token_and_process(self):
        with mock.patch.object(launcher, "read_token") as token, mock.patch.object(launcher.subprocess, "run") as run:
            self.assertEqual(self.infer(), 1)
            self.assertEqual(self.run_cli("infer", "--input-dir", str(self.root / "missing")), 1)
            token.assert_not_called()
            run.assert_not_called()
        self.assertFalse(self.outputs.exists())

    def test_positive_options_reject_bad_values(self):
        for flag in ("--batch-size", "--texture-resolution"):
            for value in ("0", "-1", "not-a-number"):
                with self.subTest(flag=flag, value=value), contextlib.redirect_stderr(self.stderr):
                    with self.assertRaises(SystemExit) as error:
                        launcher.parser().parse_args(["infer", flag, value])
                    self.assertEqual(error.exception.code, 2)

    def test_dry_run_has_no_auth_imports_process_or_filesystem_writes(self):
        self.image("a.png")
        self.secret.unlink()
        with mock.patch.dict(os.environ, {"UPSTREAM_DIR": str(self.root / "not-installed")}), \
                mock.patch.object(launcher, "read_token") as token, \
                mock.patch.object(launcher.subprocess, "run") as run:
            self.assertEqual(self.infer("--dry-run", "--low-vram-mode", "--batch-size", "2"), 0)
            token.assert_not_called()
            run.assert_not_called()
        self.assertFalse(self.outputs.exists())
        plan = json.loads(self.stdout.getvalue())
        self.assertIn("--low-vram-mode", plan["command"])
        self.assertIn("--reduction_count_type", plan["command"])
        self.assertEqual(plan["manifest"]["status"], "planned")
        self.assertEqual(plan["manifest"]["options"]["batch_size"], 2)
        self.assertNotIn(self.token, self.stdout.getvalue())

    def test_missing_or_empty_secret_cannot_fall_back_to_environment(self):
        self.image("a.png")
        with mock.patch.object(launcher.subprocess, "run") as run:
            self.secret.unlink()
            self.assertEqual(self.infer(), 1)
            self.secret.write_text("\n", encoding="utf-8")
            self.assertEqual(self.infer(), 1)
            run.assert_not_called()
        self.assertFalse(self.outputs.exists())

    def test_success_renames_outputs_and_never_persists_or_prints_token(self):
        self.image("a.jpg")
        self.image("a.png")
        self.image("CON.jpeg")
        self.assertEqual(self.infer("--low-vram-mode", "--remesh-option", "quad"), 0)
        run, manifest = self.manifest()
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual([item["output_directory"] for item in manifest["inputs"]],
                         ["0000-a", "0001-a", "0002-CON"])
        for item in manifest["inputs"]:
            self.assertTrue((run / item["output_directory"] / "mesh.glb").is_file())
            self.assertTrue((run / item["output_directory"] / "points.ply").is_file())
            self.assertFalse((run / item["upstream_directory"]).exists())
        self.assertIn("[REDACTED]", self.stdout.getvalue())
        self.assertIn(launcher.POWERED_BY, self.stdout.getvalue())
        self.assertNotIn(self.token, self.stdout.getvalue() + self.stderr.getvalue())
        self.assertNotIn(self.token, (run / "manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn(b"\r\n", (run / "manifest.json").read_bytes())

    def test_failed_process_preserves_partial_output_and_marks_manifest(self):
        self.image("a.png")
        self.image("b.png")
        with mock.patch.dict(os.environ, {"FAKE_FAIL": "1"}):
            self.assertEqual(self.infer(), 1)
        run, manifest = self.manifest()
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["returncode"], 7)
        self.assertTrue((run / "0" / "mesh.glb").is_file())
        self.assertFalse((run / "0000-a").exists())
        self.assertIn("Partial output is preserved", self.stderr.getvalue())
        self.assertNotIn(self.token, self.stdout.getvalue() + self.stderr.getvalue())
        self.assertNotIn(self.token, (run / "manifest.json").read_text(encoding="utf-8"))

    def test_successful_exit_with_missing_mesh_is_failed_without_renaming(self):
        self.image("a.png")
        self.image("b.png")
        def incomplete(command, **kwargs):
            run = Path(command[command.index("--output-dir") + 1])
            (run / "0").mkdir()
            (run / "0" / "mesh.glb").write_bytes(b"partial")
            return type("Result", (), {"stdout": ""})()
        with mock.patch.object(launcher.subprocess, "run", side_effect=incomplete) as run_process:
            self.assertEqual(self.infer(), 1)
        self.assertFalse(run_process.call_args.kwargs["shell"])
        self.assertTrue(run_process.call_args.kwargs["check"])
        run, manifest = self.manifest()
        self.assertEqual(manifest["status"], "failed")
        self.assertTrue((run / "0" / "mesh.glb").is_file())
        self.assertFalse((run / "0000-a").exists())

    def test_repeat_runs_never_overwrite_previous_output(self):
        self.image("a.png")
        self.assertEqual(self.infer(), 0)
        self.assertEqual(self.infer(), 0)
        self.assertEqual(len(list(self.outputs.iterdir())), 2)

    def test_output_names_handle_punctuation_and_reserved_names(self):
        self.assertEqual(launcher.output_name(0, Path("CON.png")), "0000-CON")
        self.assertEqual(launcher.output_name(1, Path("...png")), "0001-image")
        self.assertEqual(launcher.output_name(2, Path("a b.png")), "0002-a-b")

    def test_doctor_runs_without_reading_secret_or_downloading_models(self):
        self.secret.unlink()
        with mock.patch.object(launcher, "read_token") as token, \
                mock.patch.object(launcher.subprocess, "run") as run:
            self.assertEqual(self.run_cli("doctor"), 0)
            token.assert_not_called()
            self.assertTrue(run.call_args.kwargs["check"])
            self.assertFalse(run.call_args.kwargs["shell"])
            self.assertNotIn("HF_TOKEN", run.call_args.kwargs["env"])
            self.assertNotIn("HUGGING_FACE_HUB_TOKEN", run.call_args.kwargs["env"])
            self.assertIn("baker.rasterize", run.call_args.args[0][-1])
        self.assertIn(launcher.POWERED_BY, self.stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
