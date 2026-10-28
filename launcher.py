#!/usr/bin/env python3
"""Small, dependency-free command line wrapper around official SPAR3D inference."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
POWERED_BY = "Powered by Stability AI"


class LauncherError(Exception):
    """An actionable error that can be shown without exposing credentials."""


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    infer = commands.add_parser("infer", help="Generate meshes from local images")
    infer.add_argument("images", nargs="*", help="PNG or JPEG files")
    infer.add_argument("--input-dir", default="/data/input")
    infer.add_argument("--output-dir", default="/data/output")
    infer.add_argument("--low-vram-mode", action="store_true")
    infer.add_argument("--batch-size", type=positive_integer, default=1)
    infer.add_argument("--texture-resolution", type=positive_integer, default=1024)
    infer.add_argument("--remesh-option", choices=("none", "triangle", "quad"), default="none")
    infer.add_argument("--dry-run", action="store_true", help="Print the plan without inference or filesystem writes")
    commands.add_parser("doctor", help="Check CUDA and compiled extensions without downloading models")
    return result


def collect_images(explicit, input_dir):
    """Validate and deterministically order inputs; never recurse into directories."""
    if explicit:
        paths = [Path(value).expanduser().resolve() for value in explicit]
        for path in paths:
            if not path.is_file():
                raise LauncherError("Input file does not exist: {}".format(path))
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                raise LauncherError("Input must be PNG or JPEG: {}".format(path))
    else:
        directory = Path(input_dir).expanduser().resolve()
        if not directory.is_dir():
            raise LauncherError("Input directory does not exist: {}".format(directory))
        paths = [path.resolve() for path in directory.iterdir()
                 if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
    paths.sort(key=lambda path: (str(path).casefold(), str(path)))
    if not paths:
        raise LauncherError("No PNG or JPEG input images found")
    return paths


def output_name(index, path):
    # A numeric prefix handles duplicate stems and Windows reserved device names.
    stem = re.sub(r"[^\w.-]+", "-", path.stem, flags=re.UNICODE).strip(" .-")
    return "{:04d}-{}".format(index, (stem or "image")[:80])


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def plan_inference(args):
    images = collect_images(args.images, args.input_dir)
    upstream = Path(os.environ.get("UPSTREAM_DIR", "/opt/upstream")).expanduser().resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = Path(args.output_dir).expanduser().resolve() / (stamp + "-" + uuid.uuid4().hex[:8])
    command = [sys.executable, str(upstream / "run.py")]
    command.extend(str(path) for path in images)
    command.extend([
        "--output-dir", str(run_dir),
        "--device", "cuda",
        "--batch_size", str(args.batch_size),
        "--texture-resolution", str(args.texture_resolution),
        "--remesh_option", args.remesh_option,
        "--reduction_count_type", "keep",
    ])
    if args.low_vram_mode:
        command.append("--low-vram-mode")
    manifest = {
        "format_version": 1,
        "status": "planned",
        "created_at": utc_now(),
        "options": {
            "low_vram_mode": args.low_vram_mode,
            "batch_size": args.batch_size,
            "texture_resolution": args.texture_resolution,
            "remesh_option": args.remesh_option,
            "device": "cuda",
        },
        "inputs": [
            {"index": index, "path": str(path), "upstream_directory": str(index),
             "output_directory": output_name(index, path)}
            for index, path in enumerate(images)
        ],
    }
    return upstream, run_dir, command, manifest


def read_token():
    secret_path = Path(os.environ.get("HF_TOKEN_FILE", "/run/secrets/hf_token"))
    try:
        token = secret_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise LauncherError("Cannot read the Hugging Face token file. Set HF_TOKEN_FILE to a readable secret file.") from exc
    if not token or any(character.isspace() for character in token):
        raise LauncherError("The Hugging Face token file must contain a single nonempty token")
    return token


def write_manifest(run_dir, manifest):
    temporary = run_dir / ".manifest.json.tmp"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(run_dir / "manifest.json")


def print_child_output(output, token=None):
    if output:
        if token:
            output = output.replace(token, "[REDACTED]")
        print(output, end="" if output.endswith("\n") else "\n")


def infer(args):
    upstream, run_dir, command, manifest = plan_inference(args)
    if args.dry_run:
        print(json.dumps({"command": command, "cwd": str(upstream), "output_directory": str(run_dir),
                          "manifest": manifest}, ensure_ascii=False, indent=2))
        return 0
    if not (upstream / "run.py").is_file():
        raise LauncherError("Official run.py was not found. Build the image or set UPSTREAM_DIR.")
    token = read_token()
    child_env = os.environ.copy()
    child_env.pop("HUGGING_FACE_HUB_TOKEN", None)
    child_env["HF_TOKEN"] = token
    child_env["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "0"
    # The CLI flag, rather than an inherited setting, determines this run's mode.
    child_env.pop("SPAR3D_LOW_VRAM", None)
    child_env.pop("SPAR3D_USE_CPU", None)
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest["status"] = "running"
    write_manifest(run_dir, manifest)
    print(POWERED_BY, flush=True)
    print("Output: {}".format(run_dir), flush=True)
    print("Running inference; captured upstream output will be shown on completion.", flush=True)
    try:
        result = subprocess.run(command, cwd=upstream, env=child_env, shell=False, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        print_child_output(result.stdout, token)
        # Check every source before renaming; retain all numeric folders on an incomplete run.
        for item in manifest["inputs"]:
            source = run_dir / item["upstream_directory"]
            if not source.is_dir() or not (source / "mesh.glb").is_file():
                raise LauncherError("Inference did not produce a mesh for input index {}".format(item["index"]))
            if (run_dir / item["output_directory"]).exists():
                raise LauncherError("An unexpected output name collision occurred")
        for item in manifest["inputs"]:
            (run_dir / item["upstream_directory"]).rename(run_dir / item["output_directory"])
        manifest["status"] = "completed"
        manifest["completed_at"] = utc_now()
        write_manifest(run_dir, manifest)
    except (subprocess.CalledProcessError, OSError, LauncherError, KeyboardInterrupt) as exc:
        manifest["status"] = "failed"
        manifest["completed_at"] = utc_now()
        if isinstance(exc, subprocess.CalledProcessError):
            print_child_output(exc.stdout, token)
            manifest["returncode"] = exc.returncode
            message = "Upstream inference failed (exit {}).".format(exc.returncode)
        elif isinstance(exc, KeyboardInterrupt):
            message = "Inference was interrupted."
        elif isinstance(exc, LauncherError):
            message = str(exc)
        else:
            message = "Inference or output processing encountered a filesystem/process error."
        manifest["error"] = message
        try:
            write_manifest(run_dir, manifest)
        except OSError:
            print("Could not update the manifest after failure.", file=sys.stderr)
        raise LauncherError("{} Partial output is preserved at {}".format(message, run_dir)) from exc
    print("Completed: {}".format(run_dir))
    return 0


DOCTOR_CODE = r'''
import importlib.metadata
import json
import torch
import texture_baker
import uv_unwrapper

if not torch.cuda.is_available():
    raise SystemExit("CUDA is unavailable. Check the NVIDIA driver and container GPU access.")
uv = torch.tensor([[0.1, 0.1], [0.9, 0.1], [0.1, 0.9]], dtype=torch.float32, device="cuda")
faces = torch.tensor([[0, 1, 2]], dtype=torch.int32, device="cuda")
baker = texture_baker.TextureBaker()
rasterized = baker.rasterize(uv, faces, 32)
torch.cuda.synchronize()
if rasterized.shape != (32, 32, 4) or not bool(baker.get_mask(rasterized).any()):
    raise SystemExit("The CUDA texture-baker smoke check failed.")
versions = {}
for name in ("texture-baker", "uv-unwrapper"):
    try:
        versions[name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        versions[name] = "unknown"
print(json.dumps({"torch": torch.__version__, "cuda": torch.version.cuda,
                  "gpu": torch.cuda.get_device_name(0), "extensions": versions,
                  "texture_baker_cuda": "passed", "uv_unwrapper_import": "passed"}, indent=2))
'''


def doctor():
    print(POWERED_BY, flush=True)
    upstream = Path(os.environ.get("UPSTREAM_DIR", "/opt/upstream")).expanduser().resolve()
    if not upstream.is_dir():
        raise LauncherError("The upstream directory was not found. Run doctor inside the built image.")
    child_env = os.environ.copy()
    child_env.pop("HF_TOKEN", None)
    child_env.pop("HUGGING_FACE_HUB_TOKEN", None)
    try:
        subprocess.run([sys.executable, "-c", DOCTOR_CODE], cwd=upstream, env=child_env,
                       shell=False, check=True)
    except subprocess.CalledProcessError as exc:
        raise LauncherError("The CUDA/extension check failed (exit {}).".format(exc.returncode)) from exc
    return 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return infer(args) if args.command == "infer" else doctor()
    except LauncherError as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    except OSError:
        print("Error: Could not access a required file or start the child process.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
