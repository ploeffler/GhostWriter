/* ---------- Netz: online/offline und Erreichbarkeit von GitHub (#662) ----------
   navigator.onLine allein ist nur ein Hinweis (WLAN ohne Internet meldet „online“). Darum zusätzlich eine kleine Anfrage an GitHub
   ohne Token und ohne Zählung gegen das Limit (rate_limit), mit Zeitlimit: beim Start, bei online/offline, beim Zurückkehren in die App und
   nach einem Netzfehler mit wachsendem Abstand. Kein Dauerabfragen. */
const NET = {wasDown:false, online:typeof navigator === "undefined" ? true : navigator.onLine !== false, github:null, timer:0, wait:10000};
async function netProbe(){
  if (NET.online === false){ NET.github = false; NET.wasDown = true; netRender(); return false; }
  const ctl = typeof AbortController === "undefined" ? null : new AbortController(), to = ctl ? setTimeout(() => ctl.abort(), 5000) : 0;
  try { const r = await fetch("https://api.github.com/rate_limit", {cache:"no-store", signal:ctl && ctl.signal, headers:{Accept:"application/vnd.github+json"}}); NET.github = r.status < 500; }
  catch (e) { NET.github = false; }
  finally { if (to) clearTimeout(to); }
  netRender(); netSchedule();
  if (NET.github && typeof GW_PORTS !== "undefined" && GW_PORTS.outbox) { obRender(); if (NET.wasDown) GW_PORTS.outbox.flush(); }   // wieder da: Wartendes von selbst hochladen
  NET.wasDown = !NET.github; return NET.github;
}
function netSchedule(){
  clearTimeout(NET.timer);
  if (NET.github){ NET.wait = 10000; return; }
  NET.timer = setTimeout(netProbe, NET.wait); NET.wait = Math.min(NET.wait * 2, 300000);   // 10 s, 20 s, … höchstens 5 min
}
function netRender(){
  const el = $("net"); if (!el) return;
  const msg = NET.online === false ? "Offline – gelesen werden kann, was schon geladen ist. Speichern geht erst wieder mit Netz."
    : NET.github === false ? "Online, aber GitHub ist gerade nicht erreichbar. Speichern geht erst wieder, wenn GitHub antwortet." : "";
  el.hidden = !msg; el.className = "netbar" + (msg ? " off" : ""); el.textContent = msg;
}
function netFailed(){ NET.github = false; NET.wasDown = true; netRender(); netSchedule(); }   // von ports-web.js bei einem Netzfehler
