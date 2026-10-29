# spar3d-docker

**日本語** | [English](README.en.md) | [简体中文](README.zh-CN.md)

**Powered by Stability AI**

画像から3Dモデルを生成する[SPAR3D](https://github.com/Stability-AI/stable-point-aware-3d)を、Dockerで実行するための非公式キットです。
ビルド時に公式ソースの指定コミットを取得し、コマンドライン（CLI）から入力フォルダーの画像をまとめて処理します。
モデルの開発元はStability AIです。
このキットはStability AIとは独立して開発しており、同社による公式な提供や推奨を示すものではありません。

- GLB形式のメッシュ、PLY形式の点群、前処理済みの画像を保存します。
- 出力は実行ごとに分け、画像名を付けたサブフォルダーと実行記録を残します。
- 公式ソースと主要パッケージのバージョンを固定し、ビルド環境からGPUにアクセスできなくてもCUDA拡張をコンパイルします。
- モデルの重み、認証情報、利用者の入出力画像は、このリポジトリに含めません。

## 必要な環境

- LinuxのDocker EngineとNVIDIA Container Toolkit、またはWindowsのDocker Desktop（WSL 2バックエンドでLinuxコンテナーを使用）
- NVIDIA GPUと対応ドライバー（標準ビルドはRTX 30/40シリーズ向け）
- Docker Compose v2
- ビルドとモデル取得のためのインターネット接続、十分なディスク空き容量
- Hugging Faceアカウントと公式モデルへのアクセス権

[公式README](https://github.com/Stability-AI/stable-point-aware-3d/blob/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1/README.md#low-vram-mode)では、通常は約10.5 GB、VRAM節約モードでは約7 GBのVRAMを使用すると説明されています。
実際の使用量は入力画像、設定、実行環境によって変わります。
初回は `--low-vram-mode` を付けて実行してください。

## 使い方

### 1. 利用条件を確認する

[公式モデルページ](https://huggingface.co/stabilityai/stable-point-aware-3d)で利用条件を確認し、同意したうえでアクセスを申請してください。
[Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md)と[Acceptable Use Policy](https://stability.ai/use-policy)が適用されます。
商用利用時の登録や年間売上に関する条件は、[ライセンスの説明](docs/licensing.md)を確認してください。

### 2. ビルドとGPU確認

```sh
git clone https://github.com/SSE-C-553/spar3d-docker.git
cd spar3d-docker
docker compose build
docker compose run --rm app doctor
```

ビルドと `doctor` にHugging Faceトークンは不要です。
初回ビルドではCUDAとPyTorchを取得するため、数GB以上のダウンロードが発生します。
所要時間は回線速度とビルド環境によって変わります。

### 3. トークンをローカルに保存する

公式モデルの読み取り権限を持つHugging Faceトークンを用意します。
プロジェクト直下に `.secrets` フォルダーを作り、その中の `hf_token` というファイルにトークンだけを保存してください。
ファイル名に拡張子は付けず、BOMなしのUTF-8で保存します。

```text
spar3d-docker/
  .secrets/
    hf_token
```

`.secrets/` はGit管理とDockerビルド時の送信対象から除外しています。
トークンはCompose secretsを通じて推論用コンテナーに渡し、ランチャーが公式CLIの認証に使用します。
Dockerfile、コマンドの引数、READMEにはトークンを記入しないでください。
Gitに記録してしまったトークンは、Hugging Face側で失効させて再発行してください。

### 4. 画像を配置して生成する

`input/` に `.png`、`.jpg`、`.jpeg` の画像を入れます。
サブフォルダーは探索しません。

```sh
docker compose -f compose.yaml -f compose.auth.yaml run --rm app infer --low-vram-mode
```

特定の画像だけ処理する場合は、コンテナー内のパスを指定します。

```sh
docker compose -f compose.yaml -f compose.auth.yaml run --rm app infer /data/input/cat.png --low-vram-mode
```

初回推論で公式モデルや背景除去用モデルを取得します。
モデルキャッシュはDockerの名前付きボリュームに保存され、コンテナーを削除しても再利用できます。
取得するモデルやライブラリには、それぞれの利用条件が適用されます。

`--dry-run` を付けると、推論を実行せずに対象画像とコマンドを確認できます。
トークンの設定とモデルのダウンロードは不要です。

```sh
docker compose run --rm app infer --dry-run
```

## 出力とオプション

`output/` に実行日時（UTC）を含むフォルダーを作り、その中に画像ごとのサブフォルダーと実行記録の `manifest.json` を保存します。
画像名が重複しても番号で区別し、過去の実行結果を上書きしません。
推論に失敗した場合も、実行記録と途中までの結果を残します。
公式CLIのログにトークンが含まれていれば伏せ字に置き換え、推論の終了時にまとめて表示します。

```sh
docker compose run --rm app infer --help
```

| オプション | 内容 |
| --- | --- |
| `--low-vram-mode` | 公式のVRAM節約モードを使用 |
| `--batch-size 1` | 一度に処理する画像数 |
| `--texture-resolution 1024` | テクスチャ解像度 |
| `--remesh-option none` | `none`、`triangle`、`quad` から選択 |
| `--dry-run` | 推論せず、処理対象と実行予定を表示 |

このキットはCLIから使用します。
Web UIや外部公開用サーバーを起動する機能は含みません。

## 取得するソースと依存関係

ビルド時に取得する公式ソースは、コミット [`fdc311b`](https://github.com/Stability-AI/stable-point-aware-3d/tree/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1) に固定しています。
リンク先とDockerfileには、40文字の完全なコミットハッシュを指定しています。
公式ソースのコードは変更せず、独自のランチャーが入力の指定と出力の整理を行います。

CUDA 12.1.1のベースイメージをダイジェストで固定し、PyTorch 2.5.1とtorchvision 0.20.1を使用します。
Gitから取得するCLIPとAlphaCLIPも、コミットを固定しています。
`constraints.txt` には、パッケージの互換性を保つためのバージョン制約を記載しています。
OSのパッケージや間接的に必要になるパッケージまでは、すべて固定していません。
インストールされたPythonパッケージの一覧は、イメージ内の `/opt/launcher/installed-packages.txt` に記録されます。

## 検証状況

Dockerイメージのビルドと、RTX 4070 Ti上でのCUDA拡張の動作を確認しています。
入力画像から3Dモデルを生成する一連の処理は、まだ検証していません。
確認済みの項目と実行環境は、[検証記録](docs/validation.md)に記載しています。

GPUを使わないランチャーのテストと、Composeの構成チェックは次のコマンドで実行できます。

```sh
python -m unittest discover -s tests -v
docker compose config --quiet
```

## ライセンス

独自に作成したランチャー、Docker設定、ドキュメントには[MIT License](LICENSE)を適用しています。
SPAR3Dのコードとモデルには[Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md)が、依存ライブラリにはそれぞれのライセンスが適用されます。
[Notice](Notice)と[ライセンスおよび出典の説明](docs/licensing.md)を参照してください。
このリポジトリでは、モデルの重みやビルド済みDockerイメージを配布しません。
