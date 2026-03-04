#!/bin/bash

# エラーが発生した場合はスクリプトを終了する
set -e

# --- 変数定義 ---
# スクリプトの場所を基準にプロジェクトルートを特定
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

INPUT_DIR="${PROJECT_ROOT}/_output/out-062-annotated"
TMP_DIR="${PROJECT_ROOT}/_output/tmp/epub_build"
OUTPUT_DIR="${PROJECT_ROOT}/_output"
OUTPUT_EPUB="${OUTPUT_DIR}/out-098.html"
CSS_FILE="${PROJECT_ROOT}/_template/proc-099-epub.css"
METADATA_FILE="${PROJECT_ROOT}/_input/metadata.yaml"
PANDOC_CMD="pandoc"

# --- 実行前クリーンアップ＆準備 ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 EPUB生成処理"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 [1/6] ビルド環境を準備しています..."
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
# 結合用の一時ファイル
COMBINED_MD="$TMP_DIR/combined.md"
TOC_MD="$TMP_DIR/toc.md"
TITLE_PAGE_MD="$TMP_DIR/title_page.md"
echo "  ✓ 完了"

# --- タイトルページとメタデータの準備 ---
echo "🔍 [2/6] タイトルページと目次を生成しています..."
# metadata.yamlから情報を抽出
TITLE=$(grep '^title:' "$METADATA_FILE" | sed 's/title: *//' | tr -d "'")
AUTHOR=$(grep '^author:' "$METADATA_FILE" | sed 's/author: *//'| tr -d "'")
AUTHOR_KANA=$(grep '^author_kana:' "$METADATA_FILE" | sed 's/author_kana: *//'| tr -d "'")
TRANSLATOR=$(grep '^translator:' "$METADATA_FILE" | sed 's/translator: *//'| tr -d "'")
TRANSLATOR_KANA=$(grep '^translator_kana:' "$METADATA_FILE" | sed 's/translator_kana: *//'| tr -d "'")

# タイトルページ用のMarkdownファイルを作成
AUTHOR_LINE="${AUTHOR}（${AUTHOR_KANA}）"
TRANSLATOR_LINE="${TRANSLATOR}（${TRANSLATOR_KANA}） 訳"

cat << EOF > "$TITLE_PAGE_MD"
---
title: $TITLE
author:
  - "$AUTHOR_LINE"
  - "$TRANSLATOR_LINE"
lang: ja-JP
page-progression-direction: rtl
---
EOF

# --- 本文内目次の生成 ---
echo -e "# 目次\n" > "$TOC_MD"

# Get sorted list of markdown files
FILES=$(ls "$INPUT_DIR"/*.md | sort)

for file_path in $FILES; do
    filename=$(basename "$file_path")
    # ID is filename without extension
    id="${filename%.*}"
    
    # Get title (first H1)
    title=$(grep -m 1 '^# ' "$file_path" | sed 's/^# //')
    
    if [ -n "$title" ]; then
        echo "- [$title](#$id)" >> "$TOC_MD"
    fi
done
echo "  ✓ 完了"

# --- Markdownファイルの結合 ---
echo "🔍 [3/6] ソースファイルを結合しています..."
# 結合ファイルを初期化
> "$COMBINED_MD"

# Add TOC
cat "$TOC_MD" >> "$COMBINED_MD"
echo -e "\n" >> "$COMBINED_MD"

for file_path in $FILES; do
    filename=$(basename "$file_path")
    id="${filename%.*}"
    
    # Append content with ID added to H1 headers
    # sed command: append {#id} to lines starting with '# '
    sed "/^# /s/$/ {#$id}/" "$file_path" >> "$COMBINED_MD"
    echo -e "\n" >> "$COMBINED_MD"
done
echo "  ✓ 完了"

# --- 画像パスの修正 ---
echo "🔍 [4/6] 画像パスを修正しています..."
# Markdown内の相対画像パス ../images/ をプロジェクトルートからのパスに修正
sed -i.bak 's#\](](../images/#](_output/images/#g' "$COMBINED_MD"
echo "  ✓ 完了"

# --- PandocによるEPUB生成 ---
echo "🔍 [5/6] PandocでEPUBファイルを生成しています..."
# sedを使用してルビを変換
# 青空文庫形式のルビ |漢字《かんじ》 を <ruby>漢字<rt>かんじ</rt></ruby> に変換
sed -i.bak -E 's/\|([^《]+)《([^》]+)》/<ruby>\1<rt>\2<\/rt><\/ruby>/g' "$COMBINED_MD"

# 引用句内の改行をPandocの硬い改行（\\）に変換
sed -i.bak '/^>./ s/$/ \\/' "$COMBINED_MD"

"$PANDOC_CMD" \
    --standalone \
    --embed-resources \
    --to=html5 \
    -o "$OUTPUT_EPUB" \
    --css="$CSS_FILE" \
    --lua-filter="${PROJECT_ROOT}/_template/proc-099-epub-no_indent.lua" \
    --toc-depth=1 \
    "$TITLE_PAGE_MD" \
    "$COMBINED_MD"

if [ $? -ne 0 ]; then
    echo "❌ エラー: PandocでのEPUB生成に失敗しました。"
    exit 1
fi
echo "  ✓ 完了"

# --- 後処理 ---
echo "🔍 [6/6] 一時ファイルを削除しています..."
rm -rf "$TMP_DIR"
echo "  ✓ 完了"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 処理が正常に完了しました"
echo "📊 処理結果サマリー"
echo "  - 出力ファイル: $OUTPUT_EPUB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"