#!/usr/bin/env python3
"""
proc-001-extract-toc.py
HTMLファイルから目次情報を抽出し、CSVファイルとして出力する自動化スクリプト。
"""

import re
from pathlib import Path
import csv

# 定数定義
PROJECT_ROOT = Path.cwd()
HTML_DIR = PROJECT_ROOT / "_output" / "out-000-html"
OUTPUT_CSV = PROJECT_ROOT / "_output" / "out-001-outline.csv"

def find_html_file():
    """処理対象のHTMLファイル(*-images.html)を自動検出する"""
    html_files = list(HTML_DIR.glob("*-images.html"))
    if not html_files:
        # Fallback to any .html file if no -images.html is found
        html_files = list(HTML_DIR.glob("*.html"))
        if not html_files:
            raise FileNotFoundError(f"HTMLファイルが見つかりません: {HTML_DIR}")
    return max(html_files, key=lambda f: f.stat().st_size)

def main():
    """メイン処理"""
    print("=" * 70)
    print("  proc-001-extract-toc: 目次抽出スクリプト実行")
    print("=" * 70)
    
    try:
        html_file = find_html_file()
        print(f"[INFO] 対象HTML: {html_file.name}")
        content = html_file.read_text(encoding='utf-8')

        # TOCブロックの抽出 (h2>CONTENTSの次にある要素から抽出)
        # Gutenberg Australia形式: <h2>Contents</h2> ... <p ...> ... </p> ... <hr>
        toc_match = re.search(r'<h2>Contents</h2>(.*?)<hr>', content, re.DOTALL | re.IGNORECASE)
        
        if not toc_match:
             # フォールバック: <table> パターン
             toc_match = re.search(r'<h2>CONTENTS</h2>\s*<table.*?>(.*?)</table>', content, re.DOTALL | re.IGNORECASE)

        if not toc_match:
            raise ValueError("目次ブロック (<h2>Contents</h2>に続く範囲) が見つかりません。")
        
        toc_html = toc_match.group(1)
        
        # href属性とリンクテキストを抽出
        links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', toc_html)
        
        output_rows = []
        # ヘッダー行を追加
        output_rows.append(['type', 'title', 'section_id'])

        for i, (href, text) in enumerate(links):
            # hrefが#で始まっていない場合は付与
            if not href.startswith('#'):
                href = '#' + href
                
            title = text.strip().upper()
            
            item_type = 'chapter'
            if 'appendix' in title.lower() or 'newspeak' in title.lower():
                item_type = 'appendix'
            elif 'preface' in title.lower() or 'introduction' in title.lower():
                item_type = 'preface'

            # hrefからID部分を抽出
            link_id = href.lstrip('#')
            section_id = f"{(i+1):02d}_{link_id}"
            output_rows.append([item_type, title, section_id])
        
        # CSVファイルに書き込み
        with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerows(output_rows)
            
        print(f"[INFO] {len(output_rows)}件の目次項目を {OUTPUT_CSV.name} に出力しました。")
        print("\n✓ 処理が正常に完了しました")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")

if __name__ == '__main__':
    main()
