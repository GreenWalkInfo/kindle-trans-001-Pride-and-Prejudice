# プロセス指示書: 合本版EPUB生成 (090)

## 概要
すべての章を結合し、一冊の完全なEPUB電子書籍（合本版）を生成します。
これはプロジェクトの最終成果物となります。

## 前提条件
- `epub/proc-070-assemble.md` が完了しており、`_output/out-061-assemble/` にデータが揃っていること。
- `pandoc` がインストールされていること。

## 手順

### 1. ビルドスクリプトの実行
`epub/proc-090-build-complete.sh` を実行します。

このスクリプトは以下の処理を行います：
1. `_output/out-061-assemble/` 内の全Markdownファイルを結合。
2. `pandoc` を使用してEPUB3形式に変換。
    - スタイルシート: `_template/epub-style.css`
    - インデント制御: `_template/epub-no_indent.lua`
    - メタデータ: `_input/metadata.yaml`
3. 出力先: `_output/kdp-complete/complete.epub`（ディレクトリは自動作成）

### 2. 生成物の検証
- EpubCheckなどのツール（もしあれば）で検証。
- 目視による最終確認。

### 3. 完了
KDPへのアップロード準備が整いました。
