-- proc-099-epub-no_indent.lua (改良版)

function Para(p)
  -- 段落が空でないことを確認
  if not p.content or #p.content == 0 then
    return nil
  end
  
  -- 最初の要素を取得
  local first = p.content[1]
  
  -- Str要素であることを確認
  if first and first.t == 'Str' then
    local text = first.text
    
    -- UTF-8バイト列で直接判定（より確実）
    -- 「= E3 80 8C, 『= E3 80 8E
    local first_char = text:sub(1, 3)  -- UTF-8で日本語1文字は3バイト
    
    -- 会話開始記号の判定
    if first_char == '\u{300C}' or   -- 「
       first_char == '\u{300E}' or   -- 『
       text:sub(1,1) == '"' or       -- "
       text:sub(1,1) == "'" or       -- '
       text:sub(1,1) == '—' or       -- ダッシュ
       text:sub(1,1) == '–' or
       text:sub(1,1) == '-' then
      
      -- Divでラップしてno-indentクラスを付与
      return pandoc.Div({p}, pandoc.Attr('', {'no-indent'}))
    end
  end
  
  -- 通常の段落はそのまま
  return nil
end
