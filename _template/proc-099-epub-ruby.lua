-- Pandoc Lua filter to convert Aozora Bunko style ruby to HTML <ruby> tags.
-- Targets notations like |Kanji《kana》.

function Str(el)
  local text = el.text

  -- The pattern to find: |Base《Reading》
  -- %| escapes the pipe character for Lua patterns
  -- ([^《]+) captures the base text (one or more characters that are not '《')
  -- 《 matches the literal '《'
  -- ([^》]+) captures the reading (one or more characters that are not '》')
  -- 》 matches the literal '》'
  local pattern = "%|([^〈]+)〈([^〉]+)〉"

  -- We need to return a single inline element. A Span is suitable for this.
  -- Check if there's any match first to avoid creating empty Spans.
  local has_match = false
  for _ in text:gmatch(pattern) do
    has_match = true
    break
  end

  if not has_match then
    return nil -- No match, no change. Pandoc will handle it as a normal Str.
  end

  local parts = {}
  local last_pos = 1

  -- Loop through all matches in the string using gmatch
  for base, yomi in text:gmatch(pattern) do
    -- Find the start and end of the full match to get the preceding text
    local s, e = text:find("|" .. base .. "《" .. yomi .. "》", last_pos, true)

    if s then
      -- Add the text before the current match, if any
      if s > last_pos then
        table.insert(parts, pandoc.Str(text:sub(last_pos, s - 1)))
      end

      -- Add the ruby tag as raw HTML
      table.insert(parts, pandoc.RawInline('html', '<ruby>' .. base .. '<rp>《</rp><rt>' .. yomi .. '</rt><rp>》</rp></ruby>'))

      -- Update the last position to search from
      last_pos = e + 1
    end
  end

  -- Add any remaining text after the last match
  if last_pos <= #text then
    table.insert(parts, pandoc.Str(text:sub(last_pos)))
  end

  -- Return the collection of inlines wrapped in a Span
  return pandoc.Span(parts)
end