#!/bin/bash

# エラーが発生した場合はスクリプトを終了する
set -e

# --- 変数定義 ---
# スクリプトの場所を基準にプロジェクトルートを特定
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# 入力ディレクトリ: アセンブル結果 (proc-070の結果)
INPUT_DIR="${PROJECT_ROOT}/_output/out-061-assemble"
# 出力ディレクトリ: 合本版用
OUTPUT_DIR="${PROJECT_ROOT}/_output/kdp-complete"
# 一時作業ディレクトリ
TMP_DIR="${PROJECT_ROOT}/_output/tmp/epub_build_complete"

# 出力ファイル名
OUTPUT_EPUB="${OUTPUT_DIR}/complete.epub"

# リソースファイル
CSS_FILE="${PROJECT_ROOT}/_template/epub-style.css"
LUA_FILTER="${PROJECT_ROOT}/_template/epub-no_indent.lua"
METADATA_FILE="${PROJECT_ROOT}/_input/metadata.yaml"

# --- 実行前クリーンアップ＆準備 ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 合本版EPUB生成処理 (090)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 [1/5] ビルド環境を準備しています..."

# ディレクトリ作成
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
mkdir -p "$OUTPUT_DIR"

# 結合用の一時ファイル
COMBINED_MD="$TMP_DIR/combined.md"

echo "  ✓ 完了"

# --- Markdownファイルの結合 ---
echo "🔍 [2/5] ソースファイルを結合しています..."

# 結合ファイルを初期化
> "$COMBINED_MD"

# メタデータをYAMLフロントマターとして先頭に追加
echo "---" >> "$COMBINED_MD"
cat "$METADATA_FILE" >> "$COMBINED_MD"
# 末尾に改行がない場合に備えて改行を出力
echo "" >> "$COMBINED_MD"
echo "---" >> "$COMBINED_MD"
echo -e "\n\n" >> "$COMBINED_MD"

# INPUT_DIR内のMarkdownファイルを収集・ソートして結合
# - _single が含まれるファイルは除外 (grep -v '_single')
# - 名前順にソート (sort)
find "$INPUT_DIR" -maxdepth 1 -name "*.md" | grep -v '_single' | sort | while read file_path; do
    base_name=$(basename "$file_path" .md)
    echo "  Processing: ${base_name}.md"
    
    # ファイルの内容を読み込み、注釈IDをユニーク化してから追記
    # [^note1] -> [^filename_note1] のように変換して衝突を防ぐ
    sed "s/\[\^/\[\^${base_name}_/g" "$file_path" >> "$COMBINED_MD"
    
    # ファイル間に空行を挿入（Markdownの連結トラブル防止）
    echo -e "\n\n" >> "$COMBINED_MD"
done

if [ ! -s "$COMBINED_MD" ]; then
    echo "❌ エラー: 結合されたMarkdownファイルが空です。入力ディレクトリを確認してください: $INPUT_DIR"
    exit 1
fi

echo "  ✓ 完了"

# --- コンテンツの整形 ---
echo "🔍 [3/5] コンテンツを整形しています..."

# 1. 画像パスの修正
# Markdown内の相対画像パス ../images/ をプロジェクトルートからのパス _output/images/ に修正
sed -i.bak 's#\.\./images/#_output/images/#g' "$COMBINED_MD"

# 2. ルビ形式の変換
# 青空文庫形式 |漢字《かんじ》 -> <ruby>漢字<rt>かんじ</rt></ruby>
sed -i.bak -E 's/\|([^《]+)《([^》]+)》/<ruby>\1<rt>\2<\/rt><\/ruby>/g' "$COMBINED_MD"

echo "  ✓ 完了"

# --- PandocによるEPUB生成 ---
echo "🔍 [4/5] PandocでEPUBファイルを生成しています..."

pandoc \
    -o "$OUTPUT_EPUB" \
    -f markdown \
    -t epub3 \
    --css="$CSS_FILE" \
    --lua-filter="$LUA_FILTER" \
    --toc \
    --toc-depth=2 \
    --metadata page-progression-direction="rtl" \
    "$COMBINED_MD"

if [ $? -ne 0 ]; then
    echo "❌ エラー: PandocでのEPUB生成に失敗しました。"
    exit 1
fi
echo "  ✓ 完了"

# --- 後処理 ---
echo "🔍 [5/5] 一時ファイルを削除しています..."
rm -rf "$TMP_DIR"
echo "  ✓ 完了"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 処理が正常に完了しました"
echo "📊 処理結果サマリー"
echo "  - 出力ファイル: $OUTPUT_EPUB"
echo "  - ソースディレクトリ: $INPUT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
