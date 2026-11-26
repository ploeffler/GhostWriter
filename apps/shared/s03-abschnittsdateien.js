/* ---------- Abschnittsdateien ---------- */
function part(text, name){ const re = new RegExp("^## " + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\n\\n([\\s\\S]*?)(?=^## |(?![\\s\\S]))", "m"); const m = re.exec(text); const v = m ? m[1].trim() : ""; return v === "Offen." ? "" : v; }
const msOf = t => { const k = "\n## Manuskript\n", i = t.indexOf(k); return i < 0 ? "" : t.slice(i + k.length).trim(); };
function front(t){ const m = /^---\n([\s\S]*?)\n---\n/.exec(t); try { return (m && window.jsyaml && window.jsyaml.load(m[1])) || {}; } catch (e) { return {}; } }
function words(t){ t = t.replace(/<!--[\s\S]*?-->/g, " ").replace(/^\[\^[^\]]+\]:.*(?:\n(?: {2,}|\t).*)*/gm, " ").replace(/\[\^[^\]]+\]/g, " "); return (t.match(/[\p{L}\p{N}_][\p{L}\p{N}_'’-]*/gu) || []).length; }
const fmtNum = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
function block(md, h){
  const re = new RegExp("^## " + h.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "[ \\t]*\\n", "m"), m = re.exec(md); if (!m) return null;
  const start = m.index + m[0].length, n = /^## /m.exec(md.slice(start)); return {start, end: n ? start + n.index : md.length};
}
function setBlock(md, h, val){ const b = block(md, h); if (!b) return md; const tail = md.slice(b.end); return md.slice(0, b.start) + "\n" + (val.replace(/\s+$/, "") || "Offen.") + "\n" + (tail ? "\n" : "") + tail; }
function setFact(md, v){ return md.replace(/^(---\n[\s\S]*?^fact_check:[ \t]*)(\S+)/m, (all, a) => a + v); }
async function sha16(t){ try { const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t.trim())); return "sha256:" + [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("").slice(0, 16); } catch (e) { return null; } }
const chapters = () => S.struct || [];
const allSecs = () => chapters().flatMap(c => (c.sections || []).map(s => ({c, s})));
const cached = path => S.files.get(S.readRef + "|" + path);
async function loadSecFiles(list, label){
  let done = 0; const todo = list.filter(({s}) => !cached(s.path)).length;
  const tick = () => { const el = document.querySelector("#app .dim"); if (label && el && todo > 3) el.innerHTML = `<span class="spin"></span>${esc(label)} – Abschnitt ${done} von ${todo}`; };
  return pool(list, 10, async ({s}) => { const was = !!cached(s.path); const f = await getFile(s.path, S.readRef); if (!f.dg) f.dg = await sha16(msOf(f.text)); if (!was){ done++; tick(); } return f; });
}

