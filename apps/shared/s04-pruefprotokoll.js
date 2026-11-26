/* ---------- Prüfprotokoll (wie scripts/checks.py) ---------- */
const whenOf = e => (String(e.date || "") + (e.time ? " " + e.time : "")).trim();
function label(kind){ if (kind.startsWith("analysis:")){ const a = kind.slice(9); return ["Analyse " + (ANA[a] || a), ANA_SHORT[a] || "A"]; } return LABEL[kind] || [kind, kind[0].toUpperCase()]; }
function resolve(scope){ const sc = Array.isArray(scope) ? scope : [scope]; return allSecs().filter(({c, s}) => sc.includes("book") || sc.includes(c.id) || sc.includes(s.id)).map(({s}) => s.id); }
function nowDigest(id){ const x = allSecs().find(v => v.s.id === id); const f = x && cached(x.s.path); return f && f.dg; }
function stateOf(e, hit){
  const saved = e.digests || {}, cov = hit.filter(i => i in saved);
  if (!cov.length) return "unknown";
  let unknown = false;
  for (const i of cov){ const n = nowDigest(i); if (!n){ unknown = true; continue; } if (n !== saved[i]) return "changed"; }
  return unknown ? "unknown" : "current";
}
function localize(t){
  const [name, short] = label(t.CK_KIND), mark = MARK[t.CK_RESULT] || "";
  let suf = {changed:"*", unknown:"?"}[t.CK_STATE] || ""; if (mark === "?" && suf === "?") suf = "";
  return Object.assign(t, {CK_LABEL:name, CK_SHORT:short, CK_MARK:mark, CK_RESULT_TEXT:RES[t.CK_RESULT] || t.CK_RESULT, CK_STATE_TEXT:STATE[t.CK_STATE],
    CK_TEXT:`${name}: ${RES[t.CK_RESULT] || t.CK_RESULT}, ${t.CK_WHEN || t.CK_DATE} · ${STATE[t.CK_STATE]}` + (t.CK_PARTIAL ? " · teilweise" : ""),
    CK_TAG:short + mark + suf, CK_PILL:(name + " " + mark + suf).trim()});
}
function touching(unit){ const out = []; S.checks.forEach((e, i) => { const hit = resolve(e.scope || []).filter(x => unit.has(x)); if (hit.length) out.push([i, e, hit]); }); return out; }
function mkTag(e, hit, unit){ return localize({CK_KIND:e.kind, CK_RESULT:e.result, CK_DATE:String(e.date || ""), CK_WHEN:whenOf(e), CK_REPORT:e.report || "", CK_STATE:stateOf(e, hit), CK_PARTIAL:hit.length < unit.size ? "1" : "", CK_ID:String(e.id || ""), CK_NOTE:e.note || ""}); }
const kindOrder = k => { const i = EDITORIAL.indexOf(k); return i < 0 ? 99 : i; };
function tagsFor(ids){
  const unit = new Set(ids); if (!unit.size || !S.checks.length) return [];
  const latest = {};
  for (const [i, e, hit] of touching(unit)){ const r = rankOf(e, i); if (!latest[e.kind] || r >= latest[e.kind][0]) latest[e.kind] = [r, e, hit]; }
  return Object.entries(latest).sort((a, b) => (kindOrder(a[0]) - kindOrder(b[0])) || a[0].localeCompare(b[0])).map(([, v]) => mkTag(v[1], v[2], unit));
}
function historyFor(ids){
  const unit = new Set(ids); if (!unit.size || !S.checks.length) return [];
  const hits = touching(unit).sort((a, b) => rankOf(b[1], b[0]).localeCompare(rankOf(a[1], a[0])));
  const seen = new Set(), out = [];
  for (const [, e, hit] of hits){ if (!seen.has(e.kind)){ seen.add(e.kind); continue; } out.push(mkTag(e, hit, unit)); }
  return out;
}
const pick = (list, keys) => JSON.stringify(list.map(t => Object.fromEntries(keys.map(k => [k, t[k] || ""]))));
const J_FULL = ["CK_TAG","CK_PILL","CK_TEXT","CK_RESULT","CK_STATE","CK_REPORT"], J_SLIM = ["CK_TAG","CK_TEXT","CK_RESULT","CK_STATE","CK_REPORT"];
const J_HIST = ["CK_KIND","CK_LABEL","CK_WHEN","CK_DATE","CK_TAG","CK_MARK","CK_TEXT","CK_RESULT","CK_STATE","CK_REPORT","CK_ID","CK_NOTE"];
function recentText(){
  const seen = new Set(), out = [];
  S.checks.map((e, i) => [i, e]).sort((a, b) => rankOf(b[1], b[0]).localeCompare(rankOf(a[1], a[0]))).forEach(([, e]) => { if (seen.has(e.kind) || out.length >= 3) return; seen.add(e.kind); out.push(`${label(e.kind)[0]} ${MARK[e.result] || ""} ${e.date || ""}`.trim()); });
  return out.join(" · ");
}

