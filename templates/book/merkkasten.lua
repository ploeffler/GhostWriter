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

-- Probedruck: Marker und Statusvermerke hervorheben (scripts/assemble.py, proof)
--   [ … ]{.gwmarker}  offener Marker, z. B. [QUELLE PRÜFEN: …]
--   [ … ]{.gwstatus}  „Stand: Entwurf, nicht freigegeben“
function Span(el)
  local kind = el.classes:includes('gwmarker') and 'marker' or (el.classes:includes('gwstatus') and 'status' or nil)
  if not kind then return nil end
  if FORMAT:match('latex') then
    local cmd = kind == 'marker' and '\\gwmarker{' or '\\gwstatus{'
    local out = { pandoc.RawInline('latex', cmd) }
    for _, i in ipairs(el.content) do table.insert(out, i) end
    table.insert(out, pandoc.RawInline('latex', '}'))
    return out
  elseif FORMAT:match('docx') then
    el.attributes['custom-style'] = kind == 'marker' and 'Marker' or 'Stand'
    return el
  end
  return el
end

-- Vor- und Nachspann (#57, scripts/assemble.py)
--   # Widmung {.unnumbered .unlisted .dedication}   verborgene Überschrift der Widmung:
--       PDF und DOCX ohne Überschrift; EPUB behält sie (Abschnitt mit Rolle dedication,
--       Überschrift per CSS verborgen)
--   ::: widmung … :::                               Text der Widmung:
--       LaTeX/PDF: Umgebung gwwidmung (header.tex), eigene rechte Seite, zentriert
--       DOCX:      Absatzformat „Widmung“ (neue Seite) bzw. „Widmung Text“, danach Seitenumbruch
--       EPUB/HTML: <div class="widmung">
function Header(el)
  if el.classes:includes('dedication') and (FORMAT:match('latex') or FORMAT:match('docx')) then
    return {}
  end
  return nil
end

function Div(el)
  if not el.classes:includes('widmung') then return nil end
  if FORMAT:match('latex') then
    local out = { pandoc.RawBlock('latex', '\\begin{gwwidmung}') }
    for _, b in ipairs(el.content) do table.insert(out, b) end
    table.insert(out, pandoc.RawBlock('latex', '\\end{gwwidmung}'))
    return out
  elseif FORMAT:match('docx') then
    local out = {}
    for i, b in ipairs(el.content) do
      local style = i == 1 and 'Widmung' or 'Widmung Text'
      table.insert(out, pandoc.Div({ b }, pandoc.Attr('', {}, { { 'custom-style', style } })))
    end
    table.insert(out, pandoc.RawBlock('openxml', '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'))
    return out
  end
  return nil
end
