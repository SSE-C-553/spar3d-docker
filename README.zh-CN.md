# spar3d-docker

[日本語](README.md) | [English](README.en.md) | **简体中文**

**Powered by Stability AI**

这是一个非官方工具包，用于在 Docker 中运行可从图像生成 3D 模型的 [SPAR3D](https://github.com/Stability-AI/stable-point-aware-3d)。
构建时会获取官方源码的指定提交，然后通过命令行（CLI）批量处理输入文件夹中的图像。
模型由 Stability AI 开发。
本工具包独立于 Stability AI 开发，并非该公司的官方产品，也不代表该公司的推荐。

- 保存 GLB 格式的网格、PLY 格式的点云及预处理后的图像。
- 每次运行使用独立的输出目录，并创建以图像名称命名的子文件夹和运行记录。
- 固定官方源码及主要软件包的版本，即使构建环境无法访问 GPU，也能编译 CUDA 扩展。
- 本仓库不包含模型权重、身份验证凭据或用户的输入、输出图像。

## 环境要求

- Linux 上的 Docker Engine 和 NVIDIA Container Toolkit，或 Windows 上的 Docker Desktop（使用 WSL 2 后端和 Linux 容器）
- NVIDIA GPU 及相应驱动程序（默认构建面向 RTX 30/40 系列）
- Docker Compose v2
- 用于构建及下载模型的网络连接，以及充足的可用磁盘空间
- Hugging Face 账户及官方模型的访问权限

[官方 README](https://github.com/Stability-AI/stable-point-aware-3d/blob/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1/README.md#low-vram-mode)说明，通常需要约 10.5 GB 显存，低显存模式下约需 7 GB。
实际用量取决于输入图像、设置和运行环境。
首次运行时请添加 `--low-vram-mode`。

## 使用方法

### 1. 确认使用条款

请在[官方模型页面](https://huggingface.co/stabilityai/stable-point-aware-3d)确认并同意使用条款，然后申请访问权限。
[Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md) 和 [Acceptable Use Policy](https://stability.ai/use-policy) 适用于该模型。
商业使用时的注册要求及与年收入相关的条件，请参阅[许可说明（日文）](docs/licensing.md)。

### 2. 构建并检查 GPU

```sh
git clone https://github.com/SSE-C-553/spar3d-docker.git
cd spar3d-docker
docker compose build
docker compose run --rm app doctor
```

构建和运行 `doctor` 不需要 Hugging Face 令牌。
首次构建会下载 CUDA 和 PyTorch，下载量为数 GB 或更多。
所需时间取决于网络速度和构建环境。

### 3. 在本地保存令牌

准备一个具有官方模型读取权限的 Hugging Face 令牌。
在项目根目录中创建 `.secrets` 文件夹，并在其中创建名为 `hf_token` 的文件，只写入令牌本身。
文件名不加扩展名，使用不带 BOM 的 UTF-8 编码保存。

```text
spar3d-docker/
  .secrets/
    hf_token
```

`.secrets/` 已从 Git 跟踪范围和 Docker 构建上下文中排除。
令牌通过 Compose secrets 传入推理容器，由启动器用于官方 CLI 的身份验证。
请勿将令牌写入 Dockerfile、命令参数或 README。
如果令牌已被提交到 Git，请在 Hugging Face 上撤销该令牌并重新生成。

### 4. 放入图像并生成模型

将 `.png`、`.jpg` 或 `.jpeg` 图像放入 `input/`。
程序不会搜索子文件夹。

```sh
docker compose -f compose.yaml -f compose.auth.yaml run --rm app infer --low-vram-mode
```

如果只处理指定图像，请使用容器内的路径。

```sh
docker compose -f compose.yaml -f compose.auth.yaml run --rm app infer /data/input/cat.png --low-vram-mode
```

首次推理会下载官方模型和背景移除模型。
模型缓存保存在 Docker 命名卷中，删除容器后仍可重复使用。
下载的模型和库分别受各自使用条款的约束。

添加 `--dry-run` 可以查看待处理图像和命令，而不执行推理。
此模式不需要配置令牌或下载模型。

```sh
docker compose run --rm app infer --dry-run
```

## 输出与选项

程序会在 `output/` 中创建包含运行时间（UTC）的文件夹，并在其中保存每张图像对应的子文件夹以及运行记录 `manifest.json`。
同名图像通过编号区分，之前的运行结果不会被覆盖。
即使推理失败，也会保留运行记录和已生成的部分结果。
如果官方 CLI 的日志包含令牌，启动器会将其遮蔽，并在推理结束时统一显示日志。

```sh
docker compose run --rm app infer --help
```

| 选项 | 说明 |
| --- | --- |
| `--low-vram-mode` | 使用官方的低显存模式 |
| `--batch-size 1` | 每批处理的图像数量 |
| `--texture-resolution 1024` | 纹理分辨率 |
| `--remesh-option none` | 可选 `none`、`triangle` 或 `quad` |
| `--dry-run` | 显示待处理图像和执行计划，不进行推理 |

本工具包通过 CLI 使用。
不提供 Web UI，也不启动对外提供服务的服务器。

## 获取的源码与依赖

构建时获取的官方源码固定为提交 [`fdc311b`](https://github.com/Stability-AI/stable-point-aware-3d/tree/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1)。
链接地址和 Dockerfile 均使用完整的 40 位提交哈希。
本项目不修改官方源码，由独立的启动器负责指定输入和整理输出。

CUDA 12.1.1 基础镜像通过摘要固定，并使用 PyTorch 2.5.1 和 torchvision 0.20.1。
从 Git 获取的 CLIP 和 AlphaCLIP 也固定了提交版本。
`constraints.txt` 记录用于保持软件包兼容性的版本约束。
操作系统软件包和间接依赖的版本并未全部固定。
已安装的 Python 软件包列表记录在镜像内的 `/opt/launcher/installed-packages.txt` 中。

## 验证情况

已验证 Docker 镜像构建，以及 CUDA 扩展在 RTX 4070 Ti 上的运行。
尚未验证使用模型从图像生成 3D 模型的过程。
已验证的项目和运行环境详见[验证记录（日文）](docs/validation.md)。

可使用以下命令运行无需 GPU 的启动器测试并检查 Compose 配置。

```sh
python -m unittest discover -s tests -v
docker compose config --quiet
```

## 许可证

本项目独立编写的启动器、Docker 配置和文档采用 [MIT License](LICENSE)。
SPAR3D 的代码和模型适用 [Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md)，依赖库则适用各自的许可证。
请参阅 [Notice](Notice) 和[许可证及来源说明（日文）](docs/licensing.md)。
本仓库不分发模型权重或预构建的 Docker 镜像。
