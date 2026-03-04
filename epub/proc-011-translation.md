# proc-011-translation: セクション別翻訳の実行

## 1. 目的
`_output/out-002-split-section/` 内の各英語Markdownファイルを、これまでに作成した5つの翻訳・ルビ・注釈リソース（システムプロンプト、キャラクターDB、統一方針書、ルビ付与ルール、注釈付与ルール）を統合したプロンプトで日本語に翻訳する。
※Gemini 3.1 Proの強力な推論能力を活用し、**翻訳と同時にルビと注釈をインラインで付与した完全なMarkdown**を一度の処理で生成する。

## 2. 処理フロー概要

### 入力
- **原文Markdownファイル群**: `_output/out-002-split-section/*.md`
- **システムプロンプト**: `_output/out-003-system-prompt.md`
- **キャラクターデータベース**: `_output/out-004-character.md`
- **翻訳統一方針書**: `_output/out-005-standardize.md`
- **ルビ付与ルール**: `_output/out-006-ruby.md`
- **注釈付与ルール**: `_output/out-007-annotation.md`

### 出力
- **翻訳済みMarkdownディレクトリ**: `_output/out-011-translated/`
- **ログファイル**: `_output/logs/translation_py.log`

---

## 3. 詳細タスク

### ステップ1: 翻訳スクリプトの準備
**報告**: `[1/3] 翻訳実行スクリプトを確認します...`

**処理**:
`epub/proc-011-translation.py` が存在することを確認します。このスクリプトは以下の機能を備えています：
- Vertex AI REST API を使用した翻訳。
- **思考レベル (Thinking Level)** を `HIGH` に設定。
- 429エラー時の指数的バックオフ（待機時間の自動延長）。
- 第1章（スタイル基準）と直前の章（文脈）などの自動結合、または任意の参考ファイル指定。
- 任意の出力ファイル名指定。

### ステップ2: 翻訳の実行
**報告**: `[2/3] 翻訳を実行します...`

**処理**:
以下のコマンドで、特定の章または全ファイルを翻訳します。

**特定の章のみを翻訳する場合**:
```bash
python3 epub/proc-011-translation.py --target 03_chap03.md
```

**特定の章を翻訳し、参考にするファイルを指定する場合**:
```bash
python3 epub/proc-011-translation.py --target 03_chap03.md --references _output/out-011-translated/01_chap01.md _output/out-011-translated/02_chap02.md
```

**特定の章を翻訳し、別のファイル名で出力する場合（枝番付けなどに有用）**:
```bash
python3 epub/proc-011-translation.py --target 03_chap03.md --out-filename 03_chap03_v2.md
```

**全ファイルを一括翻訳する場合（未翻訳分のみ）**:
```bash
python3 epub/proc-011-translation.py
```

**完了報告**: `✓ 翻訳処理が完了しました。詳細は _output/logs/translation_py.log を確認してください。`

### ステップ3: 翻訳結果の検証
**報告**: `[3/3] 翻訳結果を検証します...`

**処理**:
生成されたファイルのサイズや内容、ログファイルにエラーが出ていないかを確認します。ルビや注釈が正しく付与されているかサンプリングチェックを行います。

---

## 4. エラー時の対応

### 429 Too Many Requests
スクリプトが自動的に待機時間を延ばして再試行します。頻発する場合は、一度処理を中断し、時間を置いてから再開してください。

### その他のエラー
`_output/logs/translation_py.log` を確認し、原因を特定してください。特定のファイルで失敗した場合は、`--target` オプションを使ってそのファイルだけを再試行できます。

