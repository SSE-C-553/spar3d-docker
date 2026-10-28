# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04@sha256:21196d81f56b48dbee70494d5f10322e1a77cc47ffe202a3bf68eab81533c20f AS dependencies

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/cache/huggingface \
    TORCH_HOME=/cache/torch \
    XDG_CACHE_HOME=/cache \
    HF_HUB_DISABLE_TELEMETRY=1 \
    UPSTREAM_DIR=/opt/upstream

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-dev git build-essential ninja-build cmake \
      ca-certificates libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# The public source is fetched without credentials; no model weights are fetched.
RUN git init /opt/upstream \
    && git -C /opt/upstream remote add origin https://github.com/Stability-AI/stable-point-aware-3d.git \
    && git -C /opt/upstream fetch --depth 1 origin fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1 \
    && git -C /opt/upstream checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/upstream rev-parse HEAD)" = fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1

RUN python3 -m pip install pip==25.0.1 setuptools==69.5.1 wheel==0.45.1 \
    && python3 -m pip install torch==2.5.1 torchvision==0.20.1 \
       --index-url https://download.pytorch.org/whl/cu121

COPY constraints.txt requirements.txt /opt/launcher/
RUN python3 -m pip install --no-build-isolation \
      -c /opt/launcher/constraints.txt -r /opt/launcher/requirements.txt

# Docker builds normally have no visible GPU: explicitly compile CUDA kernels.
# Override for other GPU architectures when rebuilding; defaults target RTX 30/40.
ARG TORCH_CUDA_ARCH_LIST="8.6;8.9+PTX"
ARG MAX_JOBS=2
RUN USE_CUDA=1 USE_METAL=0 USE_NATIVE_ARCH=0 \
      TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST}" MAX_JOBS="${MAX_JOBS}" \
      python3 -m pip install --no-build-isolation --no-deps \
      /opt/upstream/texture_baker /opt/upstream/uv_unwrapper \
    && python3 -m pip check \
    && python3 -m pip freeze > /opt/launcher/installed-packages.txt

FROM dependencies AS runtime
ENV NO_ALBUMENTATIONS_UPDATE=1
COPY LICENSE Notice /opt/launcher/
COPY licenses /opt/launcher/licenses
COPY launcher.py /opt/launcher/launcher.py
WORKDIR /opt/upstream
ENTRYPOINT ["python3", "/opt/launcher/launcher.py"]
CMD ["--help"]
