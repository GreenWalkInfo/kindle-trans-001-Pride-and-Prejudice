#!/usr/bin/env python3
"""
proc-002-split-section.py
HTMLをセクション分割し、画像パスを解決してMarkdownを生成する（1段階処理）
"""

import csv
import os
import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path.cwd()
HTML_DIR = PROJECT_ROOT / "_output" / "out-000-html"
CSV_FILE = PROJECT_ROOT / "_output" / "out-001-outline.csv"
OUTPUT_DIR = PROJECT_ROOT / "_output" / "out-002-split-section"
IMAGE_OUTPUT_DIR = PROJECT_ROOT / "_output" / "images"

# Project Gutenbergのヘッダー・フッターを識別するための正規表現
# アスタリスクをリテラルとして扱うために \* とエスケープする
START_MARKER_PATTERNS = [r'\*\*\* START OF .*? PROJECT GUTENBERG EBOOK .*? \*\*\*']
END_MARKER_PATTERNS = [r'\*\*\* END OF .*? PROJECT GUTENBERG EBOOK .*? \*\*\*']

# 処理中に除外するHTMLタグのパターン
EXCLUDE_PATTERNS = [r'<span class="pagenum".*?</span>']

def copy_image_to_output(img_src):
    """指定された画像ソースを_output/imagesディレクトリにコピーする"""
    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # パスの正規化
    if img_src.startswith('../'):
        img_src = img_src[3:]
    elif img_src.startswith('./'):
        img_src = img_src[2:]
    
    source_path = HTML_DIR / img_src
    if source_path.exists():
        filename = source_path.name
        dest_path = IMAGE_OUTPUT_DIR / filename
        if not dest_path.exists():
            shutil.copy2(source_path, dest_path)
        return filename
    else:
        print(f"[WARNING] Image not found: {source_path}")
        return None

def html_to_markdown(html):
    """HTMLの断片をMarkdownに変換する。画像処理もここで行う"""
    # 除外要素を削除
    for pattern in EXCLUDE_PATTERNS:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)

    # パターン0: ドロップキャップ画像 (letra) をaltテキストに置換
    html = re.sub(r'<span class="letra"[^>]*>\s*<img[^>]*alt="([^"]+)"[^>]*>\s*</span>', r'\1', html, flags=re.DOTALL | re.IGNORECASE)

    
    # パターン1: figcenterクラスを持つdiv内の画像
    def replace_figcenter(match):
        div_content = match.group(1)
        img_match = re.search(r'<img[^>]+src="([^"]+)"', div_content)
        if not img_match:
            return ""
        
        img_src = img_match.group(1)
        
        # pタグからキャプションを抽出
        caption_match = re.search(r'<p[^>]*>(.*?)</p>', div_content, re.DOTALL)
        caption_html = caption_match.group(1) if caption_match else ""
        caption = re.sub(r'<[^>]+>', '', caption_html).strip()

        filename = copy_image_to_output(img_src)
        if filename:
            return f'\n\n![{caption}](../images/{filename})\n\n'
        else:
            return f'\n\n![{caption}]()\n\n' # コピー失敗時

    html = re.sub(r'<div class="figcenter"[^>]*>(.*?)</div>', replace_figcenter, html, flags=re.DOTALL)

    # パターン2: h2タグ内の画像
    def replace_h2_image(match):
        h2_content = match.group(1)
        parts = []
        
        img_match = re.search(r'<img[^>]+src="([^"]+)"', h2_content)
        if img_match:
            img_src = img_match.group(1)
            # spanタグからキャプションを抽出（改行対応）
            caption_match = re.search(r'<span class="caption">(.*?)</span>', h2_content, flags=re.DOTALL)
            caption_html = caption_match.group(1) if caption_match else ""
            caption = re.sub(r'<[^>]+>', '', caption_html).strip()
            
            filename = copy_image_to_output(img_src)
            if filename:
                parts.append(f'![{caption}](../images/{filename})')
            else:
                parts.append(f'![{caption}]()') # コピー失敗時

        # brタグの後のテキストを章タイトルとして抽出
        text_match = re.search(r'<br\s*/*>\s*<br\s*/*>\s*([^<]+)', h2_content, re.IGNORECASE)
        if text_match:
            title = text_match.group(1).strip()
            parts.append(f'## {title}')
        else:
            # テキストが見つからない場合、h2内の他のテキストをクリーンアップして見出しにする
            clean_title = re.sub(r'<[^>]+>', '', h2_content).strip()
            clean_title = re.sub(r'\s+', ' ', clean_title)
            if clean_title:
                parts.append(f'## {clean_title}')
        
        return '\n\n' + '\n\n'.join(parts) + '\n\n'
    
    html = re.sub(r'<h2[^>]*>(.*?)</h2>', replace_h2_image, html, flags=re.DOTALL)
    
    # その他の見出し、リンク、書式設定
    html = re.sub(r'<h1[^>]*>(.*?)</h1>', lambda m: f"\n\n# {re.sub(r'<[^>]+>', '', m.group(1)).strip()}\n\n", html, flags=re.DOTALL)
    html = re.sub(r'<h3[^>]*>(.*?)</h3>', lambda m: f"\n\n### {re.sub(r'<[^>]+>', '', m.group(1)).strip()}\n\n", html, flags=re.DOTALL)
    html = re.sub(r'<a\s+href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.DOTALL)
    html = re.sub(r'<strong>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL)
    html = re.sub(r'<b>(.*?)</b>', r'**\1**', html, flags=re.DOTALL)
    html = re.sub(r'<em>(.*?)</em>', r'*\1*', html, flags=re.DOTALL)
    html = re.sub(r'<i>(.*?)</i>', r'*\1*', html, flags=re.DOTALL)
    html = re.sub(r'</?(?:em|i|strong|b)>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\n\1\n\n', html, flags=re.DOTALL)
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    
    # HTMLエンティティの置換
    for old, new in [('&nbsp;', ' '), ('&quot;', '"'), ('&amp;', '&'), ('&mdash;', '—'), ('&ndash;', '–'), ('&ldquo;', '"'), ('&rdquo;', '"'), ('&lsquo;', "'"), ('&rsquo;', "'")]:
        html = html.replace(old, new)
    
    # 空白の正規化
    html = re.sub(r'[ \t]+', ' ', html)
    html = re.sub(r' *\n *', '\n', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    lines = [line.strip() for line in html.split('\n')]
    html = '\n'.join(lines)
    html = re.sub(r'^\*\s*$', '', html, flags=re.MULTILINE)
    html = re.sub(r'\n{3,}', '\n\n', html)
    
    return html.strip()

def find_html_file():
    """処理対象のHTMLファイルを自動検出する"""
    html_files = list(HTML_DIR.glob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"HTMLファイルが見つかりません: {HTML_DIR}")
    # 'images' を含むファイル名（Project Gutenbergの画像付きHTML）を優先
    images_files = [f for f in html_files if 'images' in f.name.lower()]
    return max(images_files if images_files else html_files, key=lambda f: f.stat().st_size)

def extract_book_content(html_content):
    """HTMLからProject Gutenbergのヘッダーとフッターを除いた本文を抽出する"""
    start_pos = 0
    found_start = False
    for pattern in START_MARKER_PATTERNS:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            start_pos = match.end()
            found_start = True
            break
            
    if not found_start:
         # bodyタグを探す (Gutenberg Australiaなど)
         match = re.search(r'<body[^>]*>', html_content, re.IGNORECASE)
         if match:
             start_pos = match.end()

    end_pos = len(html_content)
    found_end = False
    for pattern in END_MARKER_PATTERNS:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            end_pos = match.start()
            found_end = True
            break
            
    if not found_end:
        # Gutenberg Australia Footer Marker
        match = re.search(r'<!--ebook footer include-->', html_content, re.IGNORECASE)
        if match:
             end_pos = match.start()
        else:
             # THE END を探す
             match = re.search(r'<h2>THE END</h2>', html_content, re.IGNORECASE)
             if match:
                 end_pos = match.end() # THE END は含めるかもしれないが、通常は直前で切る
             else:
                 # body閉じタグ
                 match = re.search(r'</body>', html_content, re.IGNORECASE)
                 if match:
                     end_pos = match.start()

    return html_content[start_pos:end_pos]

def find_section_position(html_content, section_id_from_csv, start_search_pos=0):
    """HTML内で指定されたセクションの開始位置を見つける"""
    # section_id_from_csv は "00_letter1" のような形式。 "letter1" の部分が必要
    try:
        actual_id = section_id_from_csv.split('_', 1)[1]
    except IndexError:
        actual_id = section_id_from_csv

    # id属性またはname属性を検索（Gutenberg Australiaなどの古い形式に対応）
    pattern = rf'<a\s+(?:id|name)=[\"\']?{re.escape(actual_id)}[\"\']?'
    match = re.search(pattern, html_content[start_search_pos:], re.IGNORECASE)
    return start_search_pos + match.start() if match else None

def main():
    """メイン処理"""
    print("=" * 70)
    print("  proc-002: HTMLセクション分割＆画像処理（1段階方式）")
    print("=" * 70)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    html_file = find_html_file()
    print(f"[INFO] HTMLファイル: {html_file.name}")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        full_html = f.read()
    book_html = extract_book_content(full_html)
    
    sections = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) >= 3:
                sections.append({'type': row[0], 'title': row[1], 'section_id': row[2]})
    
    print(f"[INFO] 総セクション数: {len(sections)}\n")

    # CSVから読み込んだ最初の行がヘッダーであればスキップ
    if sections and sections[0]['type'] == 'type':
        sections.pop(0)
    
    for i, section in enumerate(sections):
        start_pos = find_section_position(book_html, section['section_id'])
        if start_pos is None:
            print(f"[WARNING] Section anchor not found in HTML for ID: {section['section_id']} (Title: {section['title']})")
            continue

        # セクションの開始タグ（h1, h2, divなど）まで巻き戻す
        tag_start = book_html.rfind('<', 0, start_pos)
        if tag_start != -1:
            tag_fragment = book_html[tag_start:start_pos+20] # 少し多めに読み込む
            if re.match(r'<h[1-6]', tag_fragment.lstrip(), re.IGNORECASE) or re.match(r'<div', tag_fragment.lstrip(), re.IGNORECASE):
                start_pos = tag_start

        # 次のセクションの開始位置を終端とする
        end_pos = len(book_html)
        if i + 1 < len(sections):
            next_section_id = sections[i+1]['section_id']
            found_next_pos = find_section_position(book_html, next_section_id, start_pos + 1)
            if found_next_pos is not None:
                # 次のセクションの開始タグまで巻き戻す
                next_tag_start = book_html.rfind('<', start_pos + 1, found_next_pos)
                if next_tag_start != -1:
                    tag_fragment = book_html[next_tag_start:found_next_pos+20]
                    if re.match(r'<h[1-6]', tag_fragment.lstrip(), re.IGNORECASE) or re.match(r'<div', tag_fragment.lstrip(), re.IGNORECASE):
                        end_pos = next_tag_start
                    else:
                        end_pos = found_next_pos
                else:
                    end_pos = found_next_pos
        
        section_html = book_html[start_pos:end_pos]
        markdown_content = html_to_markdown(section_html)
        
        output_file = OUTPUT_DIR / f"{section['section_id']}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    
    print(f"\n✓ 完了: {len(sections)}個のファイルを生成")
    print(f"✓ 画像ディレクトリ: {IMAGE_OUTPUT_DIR}")

if __name__ == '__main__':
    main()