-- _template/epub-fix.lua
-- リンク元に epub:type="noteref" を付与するだけのシンプル版
-- (構造変換はPythonの後処理で行うため、ここでは行わない)

function Link(el)
  -- 脚注参照リンクの場合
  if el.classes:includes("footnote-ref") then
    el.attributes['epub:type'] = 'noteref'
  end
  return el
end
