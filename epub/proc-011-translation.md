# proc-011-translation: セクション別翻訳の実行

## 1. 目的
`_output/out-002-split-section/` 内の各英語Markdownファイルを、これまでに作成した3つの翻訳リソース（システムプロンプト、キャラクターDB、統一方針書）を統合した単一のプロンプトで日本語に翻訳する。

## 2. 処理フロー概要

### 入力
- **原文Markdownファイル群**: `_output/out-002-split-section/*.md`
- **システムプロンプト**: `_output/out-003-system-prompt.md`
- **キャラクターデータベース**: `_output/out-004-character.md`
- **翻訳統一方針書**: `_output/out-005-standardize.md`

### 出力
- **翻訳済みMarkdownディレクトリ**: `_output/out-011-translated/`
- **ファイル形式**: Markdown (`.md`)
- **ファイル名**: 原文と同じファイル名（例: `00_preface.md`, `01_chapter.md`）

---

## 3. 詳細タスク

### ステップ1: 統合翻訳プロンプトの作成
**報告**: `[1/4] 統合翻訳プロンプトを作成します...`

**処理**:
1. 以下の3つのファイルを順番に読み込む：
   - `_output/out-003-system-prompt.md`
   - `_output/out-004-character.md`
   - `_output/out-005-standardize.md`

2. 以下の構成で統合プロンプトファイル `_output/tmp/combined-translation-prompt.md` を生成：

```
# 『[作品タイトル]』翻訳プロンプト（統合版）

このプロンプトは、以下の3つの文書を統合したものです。翻訳時は必ずすべての指示に従ってください。

***

## Part 1: 翻訳システムプロンプト

[out-003-system-prompt.md の内容をそのまま挿入]

***

## Part 2: キャラクターデータベース

[out-004-character.md の内容をそのまま挿入]

***

## Part 3: 翻訳統一方針書

[out-005-standardize.md の内容をそのまま挿入]

***

## 翻訳実行指示

以下の英語Markdownを上記のすべてのルールに従って日本語に翻訳してください。

**重要事項**:
- システムプロンプトの文体方針を守ること
- キャラクターDBの話し方設定を厳守すること
- 統一方針書の表記ルールを機械的に適用すること
- **見出しの翻訳**: `## CHAPTER X` のような見出しは `## 第X章` のように、アラビア数字やローマ数字を漢数字に変換して翻訳してください。
- **画像キャプションの翻訳**: 画像参照 `![alt text](path)` のうち、`alt text`（キャプション）は必ず日本語に翻訳してください。パス部分は変更しないでください。
- **その他の英語**: 著作権表示など、本文中に残る英語も日本語に翻訳してください。
- 出力形式: Markdown形式のみ（説明や前置きは不要）
```

**完了報告**: `✓ 統合プロンプトを生成しました: _output/tmp/combined-translation-prompt.md`

---

### ステップ2: 翻訳実行スクリプトの生成
**報告**: `[2/4] 翻訳実行スクリプトを生成します...`

**処理**:
以下の内容で、翻訳を実行するためのシェルスクリプト `_output/tmp/run_translation.sh` を生成します。

```bash
#!/bin/bash

# --- 設定 ---
INPUT_DIR="_output/out-002-split-section"
OUTPUT_DIR="_output/out-011-translated"
PROMPT_FILE="_output/tmp/combined-translation-prompt.md"
LOG_DIR="_output/logs"
ERROR_LOG="${LOG_DIR}/translation_errors.log"
MAX_RETRIES=3

# --- ディレクトリとログファイルの準備 ---
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${LOG_DIR}"
# ログファイルがなければ作成
touch "${ERROR_LOG}"

# --- 翻訳関数 ---
translate_file() {
    local input_file=$1
    local filename=$(basename "$input_file")
    local output_file="${OUTPUT_DIR}/${filename}"

    # 既に正常に翻訳済みのファイルはスキップ
    if [ -f "$output_file" ] && [ -s "$output_file" ]; then
        echo "スキップ: ${filename} は既に存在します。"
        return 0
    fi

    echo "翻訳開始: ${filename}"

    # 先頭の翻訳ファイルを特定（入力ディレクトリ基準）
    local first_filename=$(ls "${INPUT_DIR}" | sort | head -n 1)
    local first_file="${OUTPUT_DIR}/${first_filename}"

    # 直前の翻訳ファイルを特定（入力ディレクトリ基準で一つ前）
    local prev_filename=$(ls "${INPUT_DIR}" | sort | grep -B 1 "${filename}" | head -n 1)
    local prev_file="${OUTPUT_DIR}/${prev_filename}"

    # grep -B 1 は自身が先頭の場合、自身のみを返すため除外
    if [ "${prev_filename}" == "${filename}" ]; then
        prev_file=""
    fi
    
    # 一時プロンプトファイルの作成
    local current_prompt="${PROMPT_FILE}.tmp.${BASHPID}"
    cp "${PROMPT_FILE}" "${current_prompt}"

    # 1. 先頭ファイルの参照（文体・用語の基準として常に参照）
    # 自分自身が先頭ファイルでない場合のみ追加
    if [ -n "$first_file" ] && [ "$(basename "$first_file")" != "$filename" ] && [ -f "$first_file" ]; then
        echo -e "\n\n***\n\n## 参考情報：第1章の翻訳（基準スタイル）\n以下は、物語の冒頭（第1章）の翻訳です。登場人物の口調や文体、ナレーションのトーンをこの基準に合わせて統一してください。\n\n" >> "${current_prompt}"
        cat "$first_file" >> "${current_prompt}"
    fi

    # 2. 直前ファイルの参照（物語の連続性のため）
    # 直前ファイルが存在し、かつ自分自身でなく、かつ先頭ファイルとも異なる場合に追加
    if [ -n "$prev_file" ] && [ "$(basename "$prev_file")" != "$filename" ] && [ -f "$prev_file" ]; then
        if [ "$prev_file" != "$first_file" ]; then
             echo -e "\n\n***\n\n## 参考情報：直前の章の翻訳（直近の文脈）\n以下は、直前の章の翻訳結果です。直近の物語の流れを一貫させるための参考にしてください。\n\n" >> "${current_prompt}"
             cat "$prev_file" >> "${current_prompt}"
        fi
    fi

    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        # geminiコマンドで翻訳を実行
        cat "${current_prompt}" "${input_file}" | gemini > "${output_file}" 2>> "${ERROR_LOG}"

        # 成功判定 (出力ファイルが空でないか)
        if [ -s "$output_file" ]; then
            echo "✓ 翻訳成功: ${filename}"
            rm -f "${current_prompt}" # 一時プロンプト削除
            return 0
        else
            retries=$((retries + 1))
            echo "⚠ 翻訳失敗、再試行します... (${retries}/${MAX_RETRIES}) > ${filename}"
            # エラーログに詳細を記録
            local timestamp=$(date)
            echo "[${timestamp}] Failed to translate ${filename} (Attempt ${retries})" >> "${ERROR_LOG}"
            rm -f "${output_file}" # 空のファイルを削除
            sleep 5 # API負荷軽減のための待機
        fi
    done

    echo "❌ 翻訳失敗 (最大再試行回数超過): ${filename}"
    rm -f "${current_prompt}" # 一時プロンプト削除
    return 1
}

# --- メイン処理 ---
export -f translate_file
export INPUT_DIR OUTPUT_DIR PROMPT_FILE ERROR_LOG MAX_RETRIES

# findでファイルを検索し、順次処理（ファイル名順にソートして処理順を担保）
find "${INPUT_DIR}" -name "*.md" | sort | while read -r file; do
    translate_file "$file"
done

echo "---"
echo "すべての翻訳処理が完了しました。"

# 最終レポート
successful_count=$(ls -1 "${OUTPUT_DIR}" | wc -l)
total_count=$(ls -1 "${INPUT_DIR}" | wc -l)
failed_count=$((total_count - successful_count))

echo "処理結果サマリー:"
echo "  - 成功: ${successful_count} / ${total_count} ファイル"
echo "  - 失敗: ${failed_count} ファイル"

if [ ${failed_count} -gt 0 ]; then
    echo "翻訳に失敗したファイルがあります。詳細は ${ERROR_LOG} を確認してください。"
fi
```

**完了報告**: `✓ 翻訳スクリプトを生成しました: _output/tmp/run_translation.sh`

---

### ステップ3: 翻訳の実行
**報告**: `[3/4] 翻訳を実行します...`

**処理**:
1. 生成したスクリプトに実行権限を付与します。
   ```
   chmod +x _output/tmp/run_translation.sh
   ```
2. 以下のコマンドで翻訳を開始します。処理には時間がかかります。

   ```bash
   bash _output/tmp/run_translation.sh
   ```

**注意事項**:
- スクリプトは、`_output/out-002-split-section/` 内の全Markdownファイルを対象に、順次翻訳を実行します。
- 未翻訳または翻訳に失敗したファイルを自動で再試行します（最大3回）。
- `gemini` コマンドへのAPIリクエストが発生します。
- エラーが発生した場合、詳細は `_output/logs/translation_errors.log` に記録されます。

**完了報告**: `✓ 翻訳処理が完了しました。`

---

### ステップ4: 翻訳結果の検証
**報告**: `[4/4] 翻訳結果を検証します...`

**処理**:
翻訳実行スクリプトの最後に表示されるサマリーと、必要に応じて以下の手動チェックで結果を確認します。

**1. ファイル数の一致**:
- `_output/out-002-split-section` と `_output/out-011-translated` のファイル数を比較します。スクリプトのサマリーで確認できます。

**2. 画像参照の保持確認**:
- `grep -c '!' _output/out-002-split-section/*.md` と `grep -c '!' _output/out-011-translated/*.md` の結果を比較します。

**3. 見出し構造の保持確認**:
- `grep -c '^##' _output/out-002-split-section/*.md` と `grep -c '^##' _output/out-011-translated/*.md` の結果を比較します。

**検証レポートの出力例**:
```
(手動で追加検証を行った場合のレポート例)

翻訳検証レポート
作成日時: YYYY-MM-DD HH:MM:SS

[ファイル数チェック]
原文合計: 63, 翻訳済み合計: 63 => ✓ OK

[画像参照チェック]
原文合計: 0, 翻訳済み合計: 0 => ✓ OK

[見出し構造チェック]
全ファイルで一致 => ✓ OK

[総合評価]
✓ 検証項目は正常に完了しました
```

**完了報告**: `✓ 検証完了: スクリプトのレポートと手動検証の結果、問題ありませんでした。`

---

## 4. エラー時の対応

### 翻訳失敗時の対応
スクリプトは失敗したファイルの翻訳を自動で再試行しますが、最大試行回数を超えても成功しないファイルがあった場合は、最終レポートに表示されます。

1.  **ログの確認**: まず `_output/logs/translation_errors.log` を開き、`gemini` コマンドから返された具体的なエラーメッセージを確認します。
2.  **原因の特定**: APIキーの問題、レート制限、プロンプトの内容など、エラーの原因を特定します。
3.  **手動での再実行**: 原因を解決した後、失敗した特定のファイルのみ手動で翻訳を実行できます。
    ```bash
    # 失敗したファイル名 (例: 01_chapter.md)
    FAILED_FILE="01_chapter.md"
    
    cat _output/tmp/combined-translation-prompt.md \
        _output/out-002-split-section/${FAILED_FILE} \
        | gemini > _output/out-011-translated/${FAILED_FILE}
    ```
4.  **スクリプトの再実行**: 多くのファイルが失敗した場合は、原因を修正した上で `bash _output/tmp/run_translation.sh` を再実行してください。スクリプトは成功済みのファイルはスキップします。

### APIレート制限への対応
`gemini` コマンドがレート制限に頻繁に達する場合は、`translate_file` 関数内の `sleep` の秒数を長くすることを検討してください。

---

## 5. 重要事項

- **一貫性の確保**: 統合プロンプトを使用することで、全セクションで一貫した翻訳品質を保証します。
- **再現性**: 同じプロンプトと原文から、同じ翻訳を再生成できます。
- **段階的実行**: まず1ファイルだけ手動で翻訳し、品質を確認してから全体を実行することを推奨します。

