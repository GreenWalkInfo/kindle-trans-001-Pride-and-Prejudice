# プロセス指示書: 分冊版プレビューHTML生成 (084)

## 概要
EPUB化（`proc-085`）を行う前に、ブラウザで手軽に内容確認・校正を行うためのプレビュー用HTMLファイルを生成します。
ソースファイルは `proc-082` で準備されたものを使用します。

## 前提条件
- `epub/proc-082-prepare-single-source.md` が実行済みであり、`.../chapXX/source/` に必要なファイル一式が揃っていること。

## 手順

### 1. ディレクトリ準備
以下のディレクトリを確認・作成します。
- `_output/out-080-single/chap[番号]/build/`
- `_output/out-080-single/chap[番号]/dist/`

### 2. ファイルの結合 (Combined Markdown作成)
**※この工程で作成する `combined.md` は `proc-085`（EPUB生成）でもそのまま利用します。**

1. `.../chap01/source/` 内のすべてのMarkdownファイル（`*.md`）を取得・ソート・連結します。
2. **メタデータ注入**: 分冊用に修正したYAMLフロントマターを先頭に付与します。
3. **画像パス修正**:
   - **プロジェクトルートからのパス**に統一します。
   - 置換後: `_output/images/`
4. **ルビ変換**: HTMLルビタグへ変換。

出力先: `_output/out-080-single/chap[番号]/build/combined.md`

### 3. PandocによるHTML生成（CSS埋め込み）
中間ファイル（`combined.md`）からHTMLを生成します。
**`--self-contained` オプションを使用し、CSSをHTMLファイル内に埋め込みます。**
画像については、Pandoc実行時にはパス解決できない（外部URL扱いにする）か、あるいはHTML生成後にパスを置換することでリンクを維持します。

1. **Pandoc実行**
   - `--css` にはプロジェクトルートからのパスを指定します。
   - `--self-contained` を付与します。
   - `--lua-filter` を使用し、会話文の字下げ解除処理を適用します。

```bash
pandoc \
    -o "_output/out-080-single/chap[番号]/dist/chap[番号].html" \
    --css="_template/epub-style.css" \
    --self-contained \
    --lua-filter="_template/epub-no_indent.lua" \
    --lua-filter="_template/epub-fix.lua" \
    --toc \
    --toc-depth=2 \
    --metadata lang="ja-JP" \
    "_output/out-080-single/chap[番号]/build/combined.md"
```

### 4. 結果の確認
出力されたHTMLファイルのパスを報告します。

```