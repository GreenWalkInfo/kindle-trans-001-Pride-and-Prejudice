# proc-031-annotation: 注釈付与処理の実行

## 1. 目的
`_output/out-021-ruby/` 内のルビ付きMarkdownファイルに対し、物語の背景知識や専門用語を補足するための注釈（脚注）を付与する。
注釈はMarkdownの標準的な脚注構文（`[^key]`）を使用する。

**注釈IDと形式の仕様**:
- **ID形式**: `nXX_YY` （n + ファイル名先頭数字 + 0埋め2桁の連番。例: `n01_01`）
- **脚注定義形式**: `[^n01_01]: 【対象単語】解説文`

## 2. 処理フロー概要

### 入力
- **ルビ付きMarkdownファイル群**: `_output/out-021-ruby/*.md`

### 出力
- **注釈付きMarkdownディレクトリ**: `_output/out-031-annotation/`
- **ログ**: `_output/logs/annotation_generation.log`

---

## 3. 詳細タスク

### ステップ1: 注釈生成用Pythonスクリプトの準備
**報告**: `[1/3] 注釈生成スクリプトを準備しています...`

**処理**:
1. プロジェクトのテンプレートディレクトリにある注釈生成スクリプト `_template/proc-031-annotation.py` を確認する。
   （存在しない場合は、以下の内容で作成する）

   **スクリプトの配置場所**: `_template/proc-031-annotation.py`
   **機能**:
   - 指定ディレクトリ内のMarkdownファイルを読み込む。
   - Vertex AI (Gemini) を使用して、本文を変更せずに注釈（脚注）のみを追記する。
   - 生成結果と原文を比較し、本文の破壊（ハルシネーション）がないか厳密にチェックする。
   - 失敗時は自動再試行する。

**完了報告**: `✓ 注釈生成スクリプトの準備が完了しました。`

---


### ステップ2: 注釈生成の実行
**報告**: `[2/3] AIによる注釈生成を実行します（時間がかかります）...`

**処理**:
以下のコマンドを実行して、Pythonスクリプトによる注釈生成を開始する。

```bash
# 出力ディレクトリの作成
mkdir -p _output/out-031-annotation
mkdir -p _output/logs

# スクリプトの実行
# 引数: 入力ディレクトリ 出力ディレクトリ
python3 _template/proc-031-annotation.py \
    --input "_output/out-021-ruby" \
    --output "_output/out-031-annotation" \
    --log "_output/logs/annotation_generation.log"
```

**注意事項**:
- 処理には数分〜数十分かかる場合があります。
- 進捗はプログレスバーで表示されます。
- エラーが発生したファイルは、原文のまま出力されるか、エラーログに記録されます。

**完了報告**: `✓ 注釈生成処理が完了しました。`

---


### ステップ3: 結果の検証
**報告**: `[3/3] 生成結果を検証しています...`

**処理**:
1. **ファイル数の確認**:
   入力ディレクトリと出力ディレクトリのファイル数が一致しているか確認する。
   ```bash
   count_in=$(ls _output/out-021-ruby/*.md | wc -l)
   count_out=$(ls _output/out-031-annotation/*.md | wc -l)
   echo "入力: $count_in, 出力: $count_out"
   ```

2. **注釈形式の確認**:
   出力ファイルにMarkdown形式の脚注（`[^...]`）が含まれているか確認する。
   ```bash
   grep -r "\[\^" _output/out-031-annotation/ | head -n 3
   ```

3. **ログの確認**:
   `_output/logs/annotation_generation.log` を確認し、"Error" や "Fallback" という記述がないかチェックする。

**完了報告**: `✓ すべての検証が完了しました。`
