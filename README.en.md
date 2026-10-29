# spar3d-docker

[日本語](README.md) | **English** | [简体中文](README.zh-CN.md)

**Powered by Stability AI**

An unofficial Docker kit for running [SPAR3D](https://github.com/Stability-AI/stable-point-aware-3d), which generates 3D models from images.
The build fetches a pinned commit of the official source, and the command-line interface (CLI) processes images from an input folder in batches.
The model is developed by Stability AI.
This kit is developed independently of Stability AI and is not an official offering or endorsement by the company.

- Saves meshes in GLB format, point clouds in PLY format, and preprocessed images.
- Keeps each run's output separate, with subfolders named after the input images and a run manifest.
- Pins the official source and key package versions, and compiles CUDA extensions even when the build environment cannot access a GPU.
- Does not include model weights, credentials, or users' input and output images in this repository.

## Requirements

- Docker Engine on Linux with NVIDIA Container Toolkit, or Docker Desktop on Windows using Linux containers with the WSL 2 backend
- An NVIDIA GPU and a compatible driver; the default build targets RTX 30/40 series GPUs
- Docker Compose v2
- Internet access for building the image and downloading models, plus sufficient free disk space
- A Hugging Face account with access to the official model

The [official README](https://github.com/Stability-AI/stable-point-aware-3d/blob/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1/README.md#low-vram-mode) reports approximately 10.5 GB of VRAM usage in standard mode and approximately 7 GB in low-VRAM mode.
Actual usage varies with the input images, settings, and runtime environment.
Include `--low-vram-mode` for your first run.

## Getting started

### 1. Review the terms of use

Review and accept the terms, then request access on the [official model page](https://huggingface.co/stabilityai/stable-point-aware-3d).
The [Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md) and [Acceptable Use Policy](https://stability.ai/use-policy) apply.
For commercial-use conditions concerning registration and annual revenue, see the [licensing guide (Japanese)](docs/licensing.md).

### 2. Build the image and check GPU support

```sh
git clone https://github.com/SSE-C-553/spar3d-docker.git
cd spar3d-docker
docker compose build
docker compose run --rm app doctor
```

Neither the build nor `doctor` requires a Hugging Face token.
The first build downloads CUDA and PyTorch, requiring several gigabytes or more of downloads.
Build time depends on your connection speed and build environment.

### 3. Save your token locally

Create a Hugging Face token with read access to the official model.
Create a `.secrets` folder in the project root, then save only the token in a file named `hf_token` inside that folder.
Use UTF-8 without a BOM and do not add a file extension.

```text
spar3d-docker/
  .secrets/
    hf_token
```

`.secrets/` is excluded from Git and the Docker build context.
The token is passed to the inference container through Compose secrets, and the launcher uses it to authenticate the official CLI.
Do not put the token in the Dockerfile, command-line arguments, or README.
If a token has been committed to Git, revoke it on Hugging Face and create a replacement.

### 4. Add images and generate models

Place `.png`, `.jpg`, or `.jpeg` images in `input/`.
Subfolders are not searched.

```sh
docker compose -f compose.yaml -f compose.auth.yaml run --rm app infer --low-vram-mode
```

To process a specific image, supply its path inside the container.

```sh
docker compose -f compose.yaml -f compose.auth.yaml run --rm app infer /data/input/cat.png --low-vram-mode
```

The first inference run downloads the official model and background-removal models.
The model cache is stored in a named Docker volume and can be reused after the container is removed.
Downloaded models and libraries are subject to their respective terms of use.

Use `--dry-run` to inspect the selected images and command without running inference.
No token setup or model downloads are required.

```sh
docker compose run --rm app infer --dry-run
```

## Outputs and options

Each run creates a folder under `output/` with a UTC timestamp in its name, containing a subfolder for each image and a `manifest.json` run record.
Duplicate image names are distinguished by numbers, and previous runs are not overwritten.
If inference fails, the run record and any partial results are retained.
If the official CLI's logs contain the token, it is redacted; the collected logs are displayed when inference finishes.

```sh
docker compose run --rm app infer --help
```

| Option | Description |
| --- | --- |
| `--low-vram-mode` | Use the official low-VRAM mode |
| `--batch-size 1` | Number of images processed at once |
| `--texture-resolution 1024` | Texture resolution |
| `--remesh-option none` | Choose from `none`, `triangle`, or `quad` |
| `--dry-run` | Show selected inputs and the planned command without running inference |

This kit is used through the CLI.
It does not include a web UI or functionality for starting a publicly accessible server.

## Source and dependencies

The official source fetched during the build is pinned to commit [`fdc311b`](https://github.com/Stability-AI/stable-point-aware-3d/tree/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1).
The link target and Dockerfile specify the full 40-character commit hash.
The official source code is left unchanged; a separate launcher selects inputs and organizes outputs.

The CUDA 12.1.1 base image is pinned by digest, and the build uses PyTorch 2.5.1 and torchvision 0.20.1.
CLIP and AlphaCLIP, fetched from Git, are also pinned to specific commits.
`constraints.txt` specifies version constraints to keep packages compatible.
Not all OS packages or transitive dependencies are pinned.
The installed Python package list is recorded in `/opt/launcher/installed-packages.txt` inside the image.

## Validation status

The Docker image build and CUDA extension functionality have been verified on an RTX 4070 Ti.
Full image-to-3D generation using the model has not been verified.
See the [validation record (Japanese)](docs/validation.md) for the checks performed and the test environment.

Run the launcher tests, which do not require a GPU, and check the Compose configuration with:

```sh
python -m unittest discover -s tests -v
docker compose config --quiet
```

## License

The launcher, Docker configuration, and documentation written for this project are licensed under the [MIT License](LICENSE).
SPAR3D code and models are covered by the [Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md), and dependency libraries retain their respective licenses.
See [Notice](Notice) and the [licensing and source attribution guide (Japanese)](docs/licensing.md).
This repository does not distribute model weights or prebuilt Docker images.
