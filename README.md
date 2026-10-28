# spar3d-docker

**Powered by Stability AI**

画像から3Dモデルを生成するための、非公式のDocker実行キットです。
[SPAR3D公式実装](https://github.com/Stability-AI/stable-point-aware-3d)を固定コミットから取得し、入力フォルダーの画像をCLIで処理します。
モデル本体の開発元はStability AIです。このプロジェクトは公式製品ではなく、提携・推奨を示すものでもありません。

- 入力画像をまとめて処理し、GLBメッシュ・PLY点群・前処理画像を保存します。
- 出力は実行ごとに分け、画像名を付けたサブフォルダーと実行記録を残します。
- ソース・主要依存のバージョンを固定し、ビルド時にGPUが見えなくてもCUDA拡張をコンパイルします。
- モデル・認証情報・利用者の入出力画像をこのリポジトリに含めません。

## 必要な環境

- LinuxのDocker Engine＋NVIDIA Container Toolkit、またはWindowsのDocker Desktop（WSL 2・Linuxコンテナー）
- NVIDIA GPUと対応ドライバー。標準ビルドの対象はRTX 30/40シリーズです。
- Docker Compose v2、ビルドとモデル取得のためのインターネット接続、十分な空きディスク
- Hugging Faceアカウントと公式モデルへのアクセス権

公式READMEでは通常約10.5 GB、low-VRAMモードでは約7 GBのVRAMが目安とされています。
実際の使用量は画像・設定・環境で変わります。
このキットではまず `--low-vram-mode` で試してください。

## 使い方

### 1. 利用条件を確認する

[公式モデルページ](https://huggingface.co/stabilityai/stable-point-aware-3d)で、利用者自身が条件を確認してアクセスを申請してください。
[Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md)と[Acceptable Use Policy](https://stability.ai/use-policy)が適用されます。
商用利用の登録や売上に関する条件は[ライセンス説明](docs/licensing.md)を確認してください。
このキットによる自動同意・アクセス制限の回避は行いません。

### 2. ビルドとGPU確認

```sh
git clone https://github.com/SSE-C-553/spar3d-docker.git
cd spar3d-docker
docker compose build
docker compose run --rm app doctor
```

ビルドと `doctor` にHugging Faceトークンは不要です。
初回ビルドはCUDA・PyTorchを取得するため、時間と数GB以上のダウンロードが必要です。

### 3. トークンをローカルに保存する

公式モデルを読み取れる権限のHugging Faceトークンを新しく用意します。
プロジェクト直下に `.secrets` フォルダーを作り、その中の `hf_token` というファイルにトークンだけを保存してください。
ファイル名に拡張子は付けず、UTF-8で保存します。

```text
spar3d-docker/
  .secrets/
    hf_token
```

`.secrets/` はGit管理とDockerビルドコンテキストの対象外です。
Compose secretsで実行中のコンテナーだけに渡し、ランチャーが子プロセスの認証に使います。
トークンをDockerfile・コマンドの引数・READMEに記入しないでください。
以前Gitに記録したトークンは再利用せず、Hugging Face側で失効・再発行してください。

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
各取得先のモデル・ライブラリには、それぞれの利用条件が適用されます。

生成前に対象画像とコマンドだけを確認できます。トークンとモデルの取得は不要です。

```sh
docker compose run --rm app infer --dry-run
```

## 出力とオプション

`output/` の実行ごとのフォルダーに、入力画像ごとのサブフォルダーと `manifest.json` を保存します。
画像名が重複しても番号で区別し、過去の実行結果を上書きしません。
失敗した実行も記録と途中の結果を残します。
公式CLIのログはトークンを伏せてから、推論の終了時にまとめて表示します。

```sh
docker compose run --rm app infer --help
```

| オプション | 内容 |
| --- | --- |
| `--low-vram-mode` | 公式のVRAM節約モードを使用 |
| `--batch-size 1` | 一度に処理する画像数 |
| `--texture-resolution 1024` | テクスチャ解像度 |
| `--remesh-option none` | `none`・`triangle`・`quad` から選択 |
| `--dry-run` | 推論せず、処理対象と実行予定を表示 |

この初期版はCLIを対象とします。Web UIや外部公開用サーバーは起動しません。

## 構成と検証範囲

公式ソースの固定先は [`fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1`](https://github.com/Stability-AI/stable-point-aware-3d/tree/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1) です。
公式ソース自体には変更を加えず、外部のランチャーが入力指定と出力整理を担当します。
CUDA 12.1.1のベースイメージはdigestまで固定し、PyTorch 2.5.1、torchvision 0.20.1を使用します。
Git依存のCLIP・AlphaCLIPもコミットを固定しています。
`constraints.txt` は互換性制約であり、OSパッケージや推移依存をすべて固定するロックファイルではありません。
実際に解決されたPython依存はイメージ内の `/opt/launcher/installed-packages.txt` に記録されます。

検証状況は [docs/validation.md](docs/validation.md) に記録します。
GPU不要のランチャーテストは次のコマンドで実行できます。

```sh
python -m unittest discover -s tests -v
docker compose config --quiet
```

## ライセンス

独自のランチャー・Docker設定・ドキュメントは[MIT License](LICENSE)です。
SPAR3Dのコード・モデルには[Stability AI Community License](licenses/STABILITY-AI-COMMUNITY-LICENSE.md)が適用されます。
環境全体やモデルがMITになることを意味しません。
[Notice](Notice) と[ライセンス・出典の説明](docs/licensing.md)を参照してください。
このリポジトリはモデル重みやビルド済みDockerイメージを配布しません。
