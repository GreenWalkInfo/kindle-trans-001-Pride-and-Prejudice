#!/bin/bash
#
# proc-000-html.sh: Project Gutenberg書籍のZIPファイル解凍スクリプト
#
# 概要:
#   _inputディレクトリ内のZIPファイルを検索し、
#   _output/out-000-htmlディレクトリに解凍します。
#
# 実行方法:
#   プロジェクトのルートディレクトリから実行してください。
#   $ bash cover/proc-000-html.sh
#

# エラー発生時にスクリプトを終了
set -e
# パイプライン内のエラーも検知
set -o pipefail

# --- カラー出力用の定義 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- ロギング関数 ---
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# --- メイン処理開始 ---
echo "========================================"
echo "  HTML ZIPファイル解凍処理を開始"
echo "========================================"
echo

# --- 1. ディレクトリパスの定義 ---
INPUT_DIR="_input"
OUTPUT_DIR="_output/out-000-html"

# --- 2. 入力ディレクトリの存在確認 ---
if [ ! -d "${INPUT_DIR}" ]; then
    log_error "入力ディレクトリ '${INPUT_DIR}' が存在しません。"
    exit 1
fi

# --- 3. 出力ディレクトリの作成 ---
log_info "出力ディレクトリを準備中..."
if [ -d "${OUTPUT_DIR}" ]; then
    log_warn "出力ディレクトリ '${OUTPUT_DIR}' は既に存在します。"
    read -p "既存のファイルを削除して続行しますか? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "${OUTPUT_DIR}"
        log_info "既存のディレクトリを削除しました。"
    else
        log_error "処理を中断しました。"
        exit 1
    fi
fi

mkdir -p "${OUTPUT_DIR}"
log_info "出力ディレクトリを作成: ${OUTPUT_DIR}"
echo

# --- 4. ZIPファイルの検索 ---
log_info "'${INPUT_DIR}' ディレクトリ内のZIPファイルを検索中..."

# ZIPファイルを配列に格納
mapfile -t ZIP_FILES < <(find "${INPUT_DIR}" -maxdepth 1 -type f -name "*.zip" 2>/dev/null)

# ZIPファイルが見つからない場合
if [ ${#ZIP_FILES[@]} -eq 0 ]; then
    log_error "'${INPUT_DIR}' 内にZIPファイルが見つかりませんでした。"
    log_error "Project GutenbergからHTMLバージョンのZIPファイルをダウンロードし、"
    log_error "'${INPUT_DIR}' ディレクトリに配置してください。"
    exit 1
fi

# 複数のZIPファイルがある場合の処理
if [ ${#ZIP_FILES[@]} -gt 1 ]; then
    log_warn "複数のZIPファイルが見つかりました:"
    for i in "${!ZIP_FILES[@]}"; do
        echo "  [$i] ${ZIP_FILES[$i]}"
    done
    echo
    read -p "解凍するファイルの番号を選択してください [0]: " SELECTION
    SELECTION=${SELECTION:-0}
    
    if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -ge ${#ZIP_FILES[@]} ]; then
        log_error "無効な選択です。"
        exit 1
    fi
    
    SOURCE_ZIP="${ZIP_FILES[$SELECTION]}"
else
    SOURCE_ZIP="${ZIP_FILES[0]}"
fi

log_info "対象ZIPファイル: ${SOURCE_ZIP}"
echo

# --- 5. ZIPファイルの解凍 ---
log_info "ZIPファイルを解凍中..."
log_info "  解凍元: ${SOURCE_ZIP}"
log_info "  解凍先: ${OUTPUT_DIR}"

if unzip -q "${SOURCE_ZIP}" -d "${OUTPUT_DIR}"; then
    log_info "解凍が正常に完了しました。"
else
    log_error "ZIPファイルの解凍に失敗しました。"
    exit 1
fi
echo

# --- 6. 解凍結果の確認 ---
log_info "解凍されたファイル一覧:"
find "${OUTPUT_DIR}" -type f | head -n 10
TOTAL_FILES=$(find "${OUTPUT_DIR}" -type f | wc -l)
if [ "${TOTAL_FILES}" -gt 10 ]; then
    echo "  ... (他 $((TOTAL_FILES - 10)) ファイル)"
fi
echo

echo "========================================"
echo "  処理が正常に完了しました"
echo "========================================"
