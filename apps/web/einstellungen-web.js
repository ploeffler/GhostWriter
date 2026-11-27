/* ---------- Einstellungen › Verbindungen, Gerät, Fehlermeldungen (#662) ----------
   Eine Gruppe erscheint erst, wenn ihre Funktion umgesetzt ist (kein toter Knopf): heute GitHub, Herkunft dieser App, Speicher, Gerät und Fähigkeiten, Fehlermeldungen.
   Schlüssel und Token werden nie mit Wert angezeigt. Messwerte des Geräts werden nur hier angezeigt und nicht übertragen. */
const SET = {back:null};
let DEVICE_COARSE = "", LAST_HDR = {};
const fmtBytes = n => n == null ? "unbekannt" : n >= 1073741824 ? (n / 1073741824).toFixed(1).replace(".", ",") + " GB" : n >= 1048576 ? (n / 1048576).toFixed(1).replace(".", ",") + " MB" : Math.max(1, Math.round(n / 1024)) + " KB";
const fmtTime = ms => new Date(ms).toLocaleString("de-AT", {day:"2-digit", month:"2-digit", year:"numeric", hour:"2-digit", minute:"2-digit"});
async function setConn(){
  const out = {login:"", repo:S.owner ? S.owner + "/" + S.repo : "", perms:null, rate:null, expires:"", error:""};
  if (!token()){ out.error = "Nicht angemeldet."; return out; }
  try { out.login = await GW_PORTS.git.me(); out.expires = LAST_HDR.expires || ""; } catch (e) { out.error = errText(e); return out; }
  if (S.owner){ try { const r = await GW_PORTS.git.repoInfo(S.owner, S.repo); out.perms = r && r.permissions || null; out.priv = r && r.private; } catch (e) {} }
  try { const r = await rest("GET", "/rate_limit"); out.rate = r && r.resources && r.resources.core; } catch (e) {}
  return out;
}
async function setDevice(){
  const d = {};
  d.secure = typeof isSecureContext !== "undefined" && isSecureContext; d.online = NET.online !== false; d.github = NET.github;
  d.indexedDB = typeof indexedDB !== "undefined"; d.serviceWorker = "serviceWorker" in navigator; d.persistApi = !!(navigator.storage && navigator.storage.persist);
  d.memoryGB = navigator.deviceMemory || null; d.cores = navigator.hardwareConcurrency || null;
  try { const e = await navigator.storage.estimate(); d.storageQuota = e.quota; d.storageUsed = e.usage; d.storageFreeGB = e.quota != null ? (e.quota - (e.usage || 0)) / 1073741824 : null; } catch (e) {}
  try { d.persisted = await navigator.storage.persisted(); } catch (e) { d.persisted = null; }
  d.pwa = !!(window.matchMedia && matchMedia("(display-mode: standalone)").matches);
  d.platform = (navigator.userAgentData && navigator.userAgentData.platform) || errBrowser().split(" · ")[1]; d.mobile = navigator.userAgentData ? navigator.userAgentData.mobile : /Mobi|Android|iPhone/.test(navigator.userAgent);
  d.builtInTranslator = typeof Translator !== "undefined"; d.builtInPrompt = typeof LanguageModel !== "undefined";
  d.microphone = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia); d.mediaRecorder = typeof MediaRecorder !== "undefined";
  d.speech = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  d.webgpu = false; d.shaderF16 = false;
  if (navigator.gpu){ try { const a = await navigator.gpu.requestAdapter(); if (a){ d.webgpu = true; d.shaderF16 = !!(a.features && a.features.has && a.features.has("shader-f16")); d.maxBuffer = a.limits && a.limits.maxBufferSize; d.maxStorageBuffer = a.limits && a.limits.maxStorageBufferBindingSize; } } catch (e) {} }
  DEVICE_COARSE = `WebGPU ${d.webgpu ? "ja" : "nein"}, ${d.memoryGB ? d.memoryGB + " GB" : "Speicher unbekannt"}`;
  return d;
}
/* Eine Funktion der Matrix gegen die Messwerte: ok | eingeschraenkt (Wert unbekannt) | nein, mit Grund */
function setEval(fn, d){
  const miss = [], unk = [];
  const test = req => { Object.entries(req).forEach(([k, v]) => {
    const have = k === "secureContext" ? d.secure : d[k];
    if (typeof v === "number"){ if (have == null) unk.push(k); else if (have < v) miss.push(k); }
    else if (v === true && !have){ if (have === null) unk.push(k); else miss.push(k); }
  }); };
  test(fn.requires || {});
  if (miss.length && fn.alternative){ const alt = Object.entries(fn.alternative).every(([k, v]) => !!d[k] === v); if (alt) miss.length = 0; }
  const reason = String((fn.reason && fn.reason.de) || "").replace(/\{(\w+)\}/g, (m, k) => (fn.requires || {})[k] != null ? (fn.requires || {})[k] : m);
  if (miss.length) return {r:"nein", why:reason};
  if (unk.length) return {r:"eingeschraenkt", why:"Messwert nicht verfügbar: " + unk.join(", ")};
  return {r:"ok", why:""};
}
async function setStore(){
  const o = {unsaved:0, bytes:0, hull:0}; try { const all = await OB.all(); o.unsaved = all.length; o.bytes = JSON.stringify(all).length; } catch (e) {}
  try { for (const k of await caches.keys()){ o.hull += (await (await caches.open(k)).keys()).length; } } catch (e) {}
  return o;
}
async function settingsView(){
  if (!SET.back || S.view !== "settings") SET.back = SET.back && S.view === "settings" ? SET.back : {view:S.view || "connect", arg:S.view === "section" ? S.sec && S.sec.id : S.chap};
  S.view = "settings"; crumbs(); busy("Einstellungen werden geladen …");
  const [conn, dev, st, matrix] = await Promise.all([setConn(), setDevice(), setStore(), fetch("faehigkeiten.json").then(r => r.json()).catch(() => null)]);
  const row = (k, v) => `<tr><td>${k}</td><td>${v}</td></tr>`, yn = v => v === true ? "ja" : v === false ? "nein" : "unbekannt", name = f => f.name.de + (f.status ? ` <span class="dim">(${esc(f.status)})</span>` : "");
  const perm = conn.perms ? [conn.perms.pull ? "Lesen" : "", conn.perms.push ? "Schreiben" : "", conn.perms.admin ? "Verwalten" : ""].filter(Boolean).join(", ") || "keine" : "–";
  const github = `<section class="card"><b>GitHub</b><table class="kv">${row("Angemeldet als", conn.login ? esc(conn.login) : `<span class="dim">${esc(conn.error || "nein")}</span>`)}${row("Token", token() ? "vorhanden (Wert wird nie angezeigt)" + (conn.expires ? ", läuft ab am " + esc(String(conn.expires).slice(0, 10)) : "") : "keiner")}${row("Repository", conn.repo ? esc(conn.repo) + (conn.priv === true ? " (privat)" : "") : "<span class=\"dim\">keines geöffnet</span>")}${row("Rechte am Repository", esc(perm))}${row("Anfragen von GitHub", conn.rate ? `${conn.rate.remaining} von ${conn.rate.limit} übrig, neu ab ${esc(fmtTime(conn.rate.reset * 1000))}` : "–")}</table>
    <div class="row" style="gap:8px"><button class="btn" data-act="set-test">Verbindung testen</button>${token() ? '<button class="btn" data-act="logout">Abmelden</button>' : ""}</div><div id="settest" class="dim" style="margin-top:6px"></div></section>`;
  const version = `<section class="card"><b>Version</b><table class="kv">${(typeof verRows === "function" ? verRows() : []).map(r => row(r[0], r[1])).join("")}</table></section>`;
  const origin = `<section class="card"><b>Herkunft dieser App</b><p class="dim" style="margin:6px 0">Diese Adresse brauchen lokale Server für ihre Freigabe (CORS, ab v2.0).</p><code id="orig">${esc(location.origin)}</code> <button class="btn" data-act="set-copy" data-text="${esc(location.origin)}">Kopieren</button></section>`;
  const speicher = `<section class="card"><b>Speicher auf diesem Gerät</b><table class="kv">${row("Belegt", `${fmtBytes(dev.storageUsed)} von ${fmtBytes(dev.storageQuota)}`)}${row("Dauerhaft angefordert", dev.persisted === true ? "ja" : dev.persisted === false ? "nein" : "unbekannt")}${row("Nicht hochgeladene Änderungen", st.unsaved ? `<b>${st.unsaved}</b> (${fmtBytes(st.bytes)})` : "keine")}${row("App-Hülle (Dateien)", String(st.hull))}</table>${dev.persisted === false && dev.persistApi ? '<button class="btn" data-act="set-persist">Dauerhaften Speicher anfordern</button>' : ""}</section>`;
  const devRows = [["System", esc(dev.platform || "unbekannt") + (dev.mobile ? " (Mobilgerät)" : "")], ["Browser", esc(errBrowser().split(" · ")[0])], ["Als App installiert", yn(dev.pwa)], ["Online", NET.online === false ? "nein" : "ja"], ["GitHub erreichbar", yn(dev.github)],
    ["WebGPU", dev.webgpu ? "ja" + (dev.shaderF16 ? ", shader-f16" : "") : "nein"], ["Arbeitsspeicher (grob)", dev.memoryGB ? dev.memoryGB + " GB" : "unbekannt (nicht jeder Browser meldet ihn)"], ["Prozessorkerne", dev.cores || "unbekannt"],
    ["Eingebaute Übersetzung / Prompt-KI", `${yn(dev.builtInTranslator)} / ${yn(dev.builtInPrompt)}`], ["Mikrofon · Aufnahme · Spracherkennung", `${yn(dev.microphone)} · ${yn(dev.mediaRecorder)} · ${yn(dev.speech)}`]];
  const mat = matrix ? matrix.functions.map(f => { const e = setEval(f, dev); const lamp = {ok:"✓ geht", eingeschraenkt:"? unklar", nein:"✗ geht nicht"}[e.r]; return `<tr><td>${name(f)}</td><td>${lamp}${e.why ? `<div class="dim">${esc(e.why)}${f.fallback && e.r === "nein" ? " · Ersatz: " + esc(f.fallback.de) : ""}</div>` : ""}</td></tr>`; }).join("") : `<tr><td colspan="2" class="dim">Die Fähigkeiten-Matrix konnte nicht geladen werden.</td></tr>`;
  const geraet = `<section class="card"><b>Gerät und Fähigkeiten</b><p class="dim" style="margin:6px 0">Die Werte bleiben auf diesem Gerät. Die Matrix legt fest, welche Funktion was braucht; was das Gerät nicht kann, bleibt ausgegraut mit Grund. Ein Probelauf für Modelle folgt mit #525.</p>
    <table class="kv">${devRows.map(r => row(r[0], r[1])).join("")}</table><table class="kv mat" style="margin-top:10px"><tr><th>Funktion</th><th>Dieses Gerät</th></tr>${mat}</table></section>`;
  const errs = errList(), fehler = `<section class="card"><b>Fehlermeldungen</b><p class="dim" style="margin:6px 0">Fehler, die diese App zeigt, merkt sie sich hier (nur Technisches, ohne Repository-, Buch- und Textnamen). „Melden“ öffnet bei GitHub ein vorausgefülltes Issue; du schickst es selbst ab. Deine Arbeit geht dabei nie verloren.</p>
    ${errs.length ? `<table class="kv">${errs.map(r => `<tr><td>${esc(fmtTime(r.zuletzt))}<div class="dim">${esc(r.klasse)} · ${r.n}×</div></td><td>${esc(r.meldung || r.schritt)}<div class="dim"><code>${esc(r.fp)}</code></div></td><td><button class="btn" data-act="err-report" data-fp="${esc(r.fp)}">Melden</button></td></tr>`).join("")}</table>` : '<p class="dim">Keine Fehler gemerkt.</p>'}
    <label style="display:block;margin-top:8px;font-size:13px"><input type="checkbox" data-act="set-device" ${store.get("gw.reportDevice") === "1" ? "checked" : ""}> Grobe Gerätewerte anhängen („${esc(DEVICE_COARSE)}“)</label>${errs.length ? '<button class="btn" style="margin-top:8px" data-act="set-clear-errors">Protokoll leeren</button>' : ""}</section>`;
  $("app").innerHTML = `<div class="one"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><b style="font-size:20px">Einstellungen › Verbindungen</b><button class="btn" data-act="set-back">Zurück</button></div>${msgBox()}${github}${version}${origin}${speicher}${geraet}${fehler}
    <p class="dim">Weitere Verbindungen (KI-Anbieter, Sprachnotizen, E-Mail-Feedback) erscheinen hier, sobald ihre Funktion umgesetzt ist.</p></div>
    <style>.kv{width:100%;border-collapse:collapse;margin:6px 0}.kv td,.kv th{padding:5px 8px;border-top:.5px solid var(--border,#d6d3c8);vertical-align:top;font-size:13px;text-align:left}.kv td:first-child{width:38%}.card{margin-bottom:12px}</style>`;
  window.scrollTo(0, 0);
}
GW_PORTS.views = {settings:settingsView};
document.addEventListener("click", async ev => {
  const g = ev.target.closest && ev.target.closest("#gear"); if (g){ ev.preventDefault(); return settingsView(); }
  const b = ev.target.closest && ev.target.closest("[data-act]"); if (!b) return;
  const a = b.dataset.act;
  if (a === "set-back"){ ev.preventDefault(); const k = SET.back || {view:"connect"}; SET.back = null; return show(k.view, k.arg); }
  if (a === "set-test"){ ev.preventDefault(); const el = $("settest"); el.textContent = "Wird geprüft …"; await netProbe(); const c = await setConn();
    el.textContent = c.error ? "Nicht in Ordnung: " + c.error : `In Ordnung: angemeldet als ${c.login}${c.perms ? ", Schreibrecht " + (c.perms.push ? "ja" : "nein") : ""}${NET.github === false ? " (GitHub gerade nicht erreichbar)" : ""}.`; }
  if (a === "set-copy"){ try { await navigator.clipboard.writeText(b.dataset.text); b.textContent = "Kopiert"; } catch (e) { b.textContent = "Nicht möglich"; } }
  if (a === "set-persist"){ try { await navigator.storage.persist(); } catch (e) {} settingsView(); }
  if (a === "set-clear-errors"){ errStore([]); settingsView(); }
});
document.addEventListener("change", ev => { if (ev.target.dataset && ev.target.dataset.act === "set-device") store.set("gw.reportDevice", ev.target.checked ? "1" : "0"); });
