# プロセス指示書: 分冊版EPUB生成 (085)

## 概要
`proc-082` で準備され、`proc-084` で結合されたソース（`.../chapXX/build/combined.md`）を使用し、KDP出版用の独立したEPUBファイルを生成します。

## 前提条件
- `epub/proc-084-generate-preview.md` が実行済みであり、`combined.md` が存在すること。
  - ※もし存在しない場合は、`proc-084` の「ファイルの結合」手順を実行して作成してください。

## 手順

### 1. ファイル確認
結合済みファイル `_output/out-080-single/chap[番号]/build/combined.md` が存在することを確認します。

### 2. PandocによるEPUB生成
以下のコマンドを実行します。
`combined.md` 内の画像パスは `_output/images/` となっているため、そのままPandocで処理可能です（プロジェクトルートで実行する場合）。

pandoc \
    -o "_output/out-080-single/chap[番号]/dist/chap[番号].epub" \
    --css="_template/epub-style.css" \
    --lua-filter="_template/epub-no_indent.lua" \
    --lua-filter="_template/epub-fix.lua" \
    --toc \
    --toc-depth=2 \
    --metadata page-progression-direction="rtl" \
    --metadata lang="ja-JP" \
    "_output/out-080-single/chap[番号]/build/combined.md"

# 4. EPUB後処理 (Kindle用脚注構造変換)
python3 _template/proc-post-process-epub.py "_output/out-080-single/chap[番号]/dist/chap[番号].epub"

### 5. 後処理
出力されたEPUBファイルのパス（例: `_output/out-080-single/chap01/dist/chap01.epub`）を報告してください。