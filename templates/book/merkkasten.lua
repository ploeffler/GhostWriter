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

-- Vorwort, Nachwort (#58): ::: signatur … ::: mit Verfasser und Ort/Datum, rechtsbündig
--   LaTeX/PDF: flushright · DOCX: Absatzformat „Signatur“ · EPUB/HTML: <div class="signatur">
local DivMatter = Div
function Div(el)
  if el.classes:includes('signatur') then
    if FORMAT:match('latex') then
      local out = { pandoc.RawBlock('latex', '\\begin{flushright}\\itshape') }
      for _, b in ipairs(el.content) do table.insert(out, b) end
      table.insert(out, pandoc.RawBlock('latex', '\\end{flushright}'))
      return out
    elseif FORMAT:match('docx') then
      el.attributes['custom-style'] = 'Signatur'
      return el
    end
    return nil
  end
  return DivMatter(el)
end

-- Initialen am Kapitelanfang (#68, typesetting.initials; build_edition setzt -M gw-initials=true)
--   Erster Absatz nach jeder Kapitelüberschrift (Ebene 1, nicht unnummeriert):
--   LaTeX/PDF: \lettrine{E}{rstes} … · EPUB/HTML: <div class="initial"> (CSS ::first-letter) · DOCX: unverändert
local function initial_para(para)
  local first = para.content[1]
  if not first or first.t ~= 'Str' then return nil end
  local s = first.text
  local n = utf8.offset(s, 2) or (#s + 1)
  local letter, rest = s:sub(1, n - 1), s:sub(n)
  if not letter:match('%w') and not letter:match('[\128-\255]') then return nil end
  if FORMAT:match('latex') then
    local out = { pandoc.RawInline('latex', '\\lettrine{' .. letter .. '}{' .. rest .. '}') }
    for i = 2, #para.content do table.insert(out, para.content[i]) end
    return pandoc.Para(out)
  elseif FORMAT:match('html') or FORMAT:match('epub') then
    return pandoc.Div({ para }, pandoc.Attr('', { 'initial' }, {}))
  end
  return nil
end

function Pandoc(doc)
  local flag = doc.meta['gw-initials']
  if not flag or pandoc.utils.stringify(flag) ~= 'true' then return nil end
  local want = false
  for i, b in ipairs(doc.blocks) do
    if b.t == 'Header' and b.level == 1 then
      want = not b.classes:includes('unnumbered')
    elseif want and b.t == 'Para' then
      local first = b.content[1]
      -- Untertitel (*…*) und Statusvermerke im Probedruck überspringen, dann der erste echte Absatz
      if first and first.t ~= 'Emph' and first.t ~= 'Span' then
        local repl = initial_para(b)
        if repl then doc.blocks[i] = repl end
        want = false
      end
    end
  end
  return doc
end
