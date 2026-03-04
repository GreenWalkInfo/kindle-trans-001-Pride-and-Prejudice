import zipfile
import os
import shutil
import sys
from pathlib import Path
from lxml import etree

def clean_epub(epub_path):
    """
    EPUBファイルから構造を修正する（脚注のaside変換等）
    """
    epub_path = Path(epub_path).resolve()
    temp_dir = epub_path.parent / "epub_cleanup_temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()

    print(f"INFO: Checking EPUB: {epub_path}")

    # 解凍
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # XHTMLファイルの修正
    text_dir = temp_dir / "EPUB" / "text"
    if text_dir.exists():
        ns = {
            'xhtml': 'http://www.w3.org/1999/xhtml',
            'epub': 'http://www.idpf.org/2007/ops'
        }
        
        for xhtml_file in text_dir.glob("*.xhtml"):
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # <br>の修正 (PandocがHTML5として出力した場合の対応)
            if "<br>" in content:
                content = content.replace("<br>", "<br />")
            
            try:
                parser = etree.XMLParser(remove_blank_text=True)
                root = etree.fromstring(content.encode('utf-8'), parser=parser)
                tree = etree.ElementTree(root)
            except etree.XMLSyntaxError as e:
                print(f"WARN: XML Parse Error ({xhtml_file.name}): {e}")
                continue

            modified = False

            # ----------------------------------------------------------------
            # 注釈番号の数字表記統一 (1桁→全角)
            # ----------------------------------------------------------------
            to_fullwidth = str.maketrans("0123456789", "０１２３４５６７８９")

            for a_tag in root.findall(".//xhtml:a", ns):
                is_target = False
                cls = a_tag.get("class", "")
                epub_type = a_tag.get("{http://www.idpf.org/2007/ops}type", "")

                if "footnote-ref" in cls or "noteref" in epub_type or "footnote-back" in cls:
                    is_target = True
                
                if is_target and a_tag.text:
                    text = a_tag.text.strip()
                    if text.isdigit() and len(text) == 1:
                        new_text = text.translate(to_fullwidth)
                        if new_text != text:
                            a_tag.text = new_text
                            modified = True

            # ----------------------------------------------------------------
            # 注釈セクションの構造変換 (Popup Footnote対応)
            # ----------------------------------------------------------------
            # <section class="footnotes"> ... <ol> ... <li> ...
            # -> <aside epub:type="footnote"> ... </aside>
            
            footnotes_section = None
            for section in root.findall(".//xhtml:section", ns):
                cls = section.get("class", "")
                if "footnotes" in cls:
                    footnotes_section = section
                    break
            
            if footnotes_section is not None:
                print(f"INFO: Converting footnotes in {xhtml_file.name}")
                ol = footnotes_section.find(".//xhtml:ol", ns)
                
                if ol is not None:
                    created_asides = []
                    
                    for li in ol.findall("xhtml:li", ns):
                        fn_id = li.get("id")
                        fn_num_str = fn_id.replace("fn", "") if fn_id else ""
                        
                        # バックリンク情報の取得と削除
                        backlink_href = ""
                        for a_tag in li.findall(".//xhtml:a", ns):
                            if "footnote-back" in a_tag.get("class", "") or a_tag.get("role") == "doc-backlink":
                                backlink_href = a_tag.get("href")
                                # 親から削除
                                a_tag.getparent().remove(a_tag)
                                break
                        
                        # 数字の整形
                        display_num = fn_num_str
                        if fn_num_str.isdigit():
                            if len(fn_num_str) == 1:
                                display_num = fn_num_str.translate(to_fullwidth)
                            # 2桁以上の縦中横はCSSで対応するか、ここでspanを入れる
                        
                        # aside要素の作成
                        aside = etree.Element(f"{{{ns['xhtml']}}}aside")
                        aside.set("{http://www.idpf.org/2007/ops}type", "footnote")
                        if fn_id:
                            aside.set("id", fn_id)
                        
                        # コンテンツの移動
                        first_p = True
                        for child in li:
                            new_child = child
                            
                            # 最初のPタグにバックリンク（戻り）を追加
                            if new_child.tag == f"{{{ns['xhtml']}}}p" and first_p:
                                # <a href="..." class="footnote-back">番号</a> を作成
                                link_html = f'<a href="{backlink_href}" class="footnote-back">{display_num}</a>'
                                link_elem = etree.fromstring(link_html)
                                
                                # 先頭に挿入
                                new_child.insert(0, link_elem)
                                
                                # テキスト調整（全角スペースなど）
                                link_elem.tail = "　" + (new_child.text if new_child.text else "")
                                new_child.text = None
                                first_p = False
                            
                            aside.append(new_child)
                        
                        created_asides.append(aside)

                    # olを削除し、asideを追加
                    footnotes_section.remove(ol)
                    for aside in created_asides:
                        footnotes_section.append(aside)
                    
                    modified = True

            if modified:
                tree.write(str(xhtml_file), encoding='utf-8', xml_declaration=True, pretty_print=True)

    # 再圧縮
    print("INFO: Rebuilding EPUB...")
    if epub_path.exists():
        epub_path.unlink()

    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        for file_path in temp_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_dir)
                zip_out.write(file_path, arcname)

    # クリーンアップ
    shutil.rmtree(temp_dir)
    print("INFO: Done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 proc-post-process-epub.py <epub_file>")
        sys.exit(1)
    
    clean_epub(sys.argv[1])
