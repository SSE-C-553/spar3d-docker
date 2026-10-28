# ライセンスと配布範囲

確認日: 2026-10-29

**Powered by Stability AI**

`spar3d-docker` は個人による非公式の実行環境です。
独自に作成したランチャー、コンテナー設定、テスト、説明文には [MIT License](../LICENSE) を適用します。
上流コード・モデル・依存ライブラリの権利や利用条件は、それぞれのライセンスに従います。

## 上流の取得と表示

ビルド時に [SPAR3D の固定コミット](https://github.com/Stability-AI/stable-point-aware-3d/tree/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1) を取得します。
上流ソースは変更せず、外部のランチャーから入力と出力先を指定します。
このリポジトリは上流ソース、モデル重み、ビルド済みコンテナーイメージを配布しません。

固定コミットの [公式ライセンス原文](https://github.com/Stability-AI/stable-point-aware-3d/blob/fdc311b16809e6a8adc2f5a3407ebb3db1a95bd1/LICENSE.md) は 2024-07-05 版の Stability AI Community License です。
[全文の写し](../licenses/STABILITY-AI-COMMUNITY-LICENSE.md) と [Notice](../Notice) を同梱し、上流のライセンスもビルド先に保持します。
第 IV(a) 節は、本体・派生物やそれらを使用する製品等の提供時に、契約の写し、指定の著作権表示、目立つ帰属表示を求めています。
将来上流を改変する場合は、その内容も Notice に記載してください。

## モデルを利用する人が確認する条件

- [公式モデルページ](https://huggingface.co/stabilityai/stable-point-aware-3d) で各利用者が取得条件に同意し、自分のトークンで実行時にダウンロードします。
  トークンは実行時にファイルとして渡し、Git やビルドイメージへ保存しません。
- 商用利用には [Stability AI への登録](https://stability.ai/community-license) が規定されています。
  固定版の第 III 節では、本人・関連会社の合計年間売上が USD 1,000,000 を超える場合の契約終了と、別ライセンスの取得が規定されています。
  モデルカードの短い説明には表記の不一致があるため、条件の判断には原文と [公式案内](https://stability.ai/license) を確認してください。
- 利用と生成物には [Acceptable Use Policy](https://stability.ai/use-policy) が適用されます。
  確認時点の発効日は 2026-09-30 です。
  元の契約は更新される AUP を参照しているため、利用時にも確認してください。
- 第 IV(b) 節には、本体・派生物・生成物を用いた別の基盤生成 AI モデルの作成・改善に関する制限があります。
  第 IV(c)(i) 節は商標の利用許諾を与えません。
  このプロジェクトの表示は出典と必要な帰属を示すもので、公式提供や推奨を意味しません。

この説明は原文を置き換えるものではありません。
契約上の例外や個別の商用利用条件は原文を確認し、必要に応じて [Stability AI](https://stability.ai/enterprise) に問い合わせてください。

## 依存関係

ビルド時に取得する依存関係には、個別のライセンスが適用されます。
Git から取得する以下の直接依存はコミットを固定しています。

| 依存 | 固定コミット | ライセンス原文 |
| --- | --- | --- |
| CLIP | `d05afc436d78f1c48dc0dbf8e5980a9d471f35f6` | [MIT](https://github.com/openai/CLIP/blob/d05afc436d78f1c48dc0dbf8e5980a9d471f35f6/LICENSE) |
| AlphaCLIP | `ef9262bc539728bf8ef2dfe9c402ae12bbfcd9ff` | [Apache-2.0](https://github.com/SunzeY/AlphaCLIP/blob/ef9262bc539728bf8ef2dfe9c402ae12bbfcd9ff/LICENSE) |

この表は全依存関係の一覧ではありません。
本プロジェクトの MIT License が環境全体を再許諾することはありません。
利用者がコンテナーイメージ等を再配布する場合は、OS・CUDA・Python パッケージ・追加モデルを含む実際の内容について、元のライセンス・著作権表示・必要なソース提供等の条件を個別に確認してください。
