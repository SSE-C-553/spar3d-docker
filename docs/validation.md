# 検証記録

検証日: 2026-10-29

## 確認環境

| 項目 | 値 |
| --- | --- |
| ホスト | Windows、Docker DesktopのWSL 2 Linuxバックエンド |
| Docker Engine | 27.2.0 |
| Docker Compose | 2.29.2-desktop.2 |
| GPU | NVIDIA GeForce RTX 4070 Ti、12282 MiB |
| NVIDIAドライバー | 610.88 |
| コンテナー | Ubuntu 22.04、Python 3.10、CUDA 12.1.1 |
| PyTorch / torchvision | 2.5.1+cu121 / 0.20.1+cu121 |

## 成功した確認

- Dockerイメージの実ビルド。GPUを公開していないビルド工程でCUDA拡張をコンパイル。
- `pip check` による依存関係の整合性確認。
- `docker compose run --rm app doctor`。GPU認識、texture-bakerのCUDAラスタライズ、uv-unwrapperのimportに成功。
- ネットワークを無効にしたコンテナーで、公式 `run.py --help` の起動に成功。モデル重みは取得していない。
- 公式ソースに含まれる `fish.png` を指定したランチャーの `--dry-run`。トークンなしで処理計画を表示し、生成ファイルを作らない。
- ランチャーの12件のテスト。入力検証、同名画像の出力整理、実行間の上書き防止、失敗時の保存、トークンのログ伏字等を検証。
- 基本Composeと認証用Composeの構成チェック。
- 配布対象ファイルのUTF-8 without BOM / LF、認証情報らしき文字列の有無、秘密ファイルと入出力のGit除外を確認。

Fletは、背景除去ライブラリが要求する範囲に合う `0.23.2` を指定した。
実際に解決された主な推移依存は `albumentations==1.4.15`、`albucore==0.0.16`、`timm==1.0.30`。
全Python依存の記録は、ビルド済みイメージ内の `/opt/launcher/installed-packages.txt` にある。

## まだ確認していないこと

公式モデルのダウンロードと、モデルを用いた画像から3Dへの推論は未実施。
既存の認証情報は再利用せず、新しいトークンと利用者自身のモデルアクセス権で確認する必要がある。
生成品質、実推論時のVRAM使用量・速度、別GPUでの動作は、この確認結果から保証できない。

入力検証・出力整理のテストでは軽量な代替CLIを使用しているため、モデル推論の検証とは区別する。
公式CLIを読み込む際のtimmの非推奨import警告は残っているが、起動・GPU拡張の確認は成功した。
