-- GhostWriter: Merkkästen und Quellen für den Buchsatz
--
-- Ein Zitatblock, der mit **Merkkasten** beginnt, wird zu einem Merkkasten:
--   LaTeX/PDF: Umgebung gwmerkkasten (tcolorbox, siehe header.tex)
--   DOCX:      Absatzformat „Merkkasten“ (reference.docx aus build_edition.py)
--   EPUB/HTML: <div class="merkkasten">
-- Das Wort „Merkkasten“ selbst wird als kleine Überschrift im Kasten gezeigt.

local function is_merkkasten(el)
  local first = el.content[1]
  if not first or first.t ~= 'Para' then return false end
  local i1 = first.content[1]
  return i1 and i1.t == 'Strong' and pandoc.utils.stringify(i1) == 'Merkkasten'
end

local function strip_label(el)
  local first = el.content[1]
  table.remove(first.content, 1)
  while first.content[1] and (first.content[1].t == 'Space' or first.content[1].t == 'SoftBreak') do
    table.remove(first.content, 1)
  end
  return el.content
end

function BlockQuote(el)
  if not is_merkkasten(el) then return nil end
  local body = strip_label(el)
  if FORMAT:match('latex') then
    local out = { pandoc.RawBlock('latex', '\\begin{gwmerkkasten}') }
    for _, b in ipairs(body) do table.insert(out, b) end
    table.insert(out, pandoc.RawBlock('latex', '\\end{gwmerkkasten}'))
    return out
  elseif FORMAT:match('docx') then
    local inner = { pandoc.Para({ pandoc.Strong({ pandoc.Str('Merkkasten') }) }) }
    for _, b in ipairs(body) do table.insert(inner, b) end
    return pandoc.Div(inner, pandoc.Attr('', {}, { { 'custom-style', 'Merkkasten' } }))
  else
    local inner = { pandoc.Para({ pandoc.Strong({ pandoc.Str('Merkkasten') }) }) }
    for _, b in ipairs(body) do table.insert(inner, b) end
    return pandoc.Div(inner, pandoc.Attr('', { 'merkkasten' }, {}))
  end
end
