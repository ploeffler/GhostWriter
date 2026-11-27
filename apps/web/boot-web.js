S.mcp = null; S.sample = null; S.ready = true;   // kein Konnektor, keine KI in dieser Fassung (Stufe 1, #662)
document.addEventListener("submit", async ev => {
  if (ev.target.id !== "fToken") return;
  ev.preventDefault();
  const v = $("tokenIn").value.trim();
  if (!v) return;
  store.set(TOKEN_KEY, v);
  try { const who = await GW_PORTS.git.me(); S.login = who || ""; S.msg = null; }
  catch (e) { store.set(TOKEN_KEY, ""); S.msg = {kind:"err", html:esc(errText(e))}; }
  show("connect");
});
document.addEventListener("click", async ev => {
  const f = ev.target.closest && ev.target.closest('[data-act="outbox-flush"]');
  if (f){ ev.preventDefault(); await netProbe(); await GW_PORTS.outbox.flush(); return; }
  const b = ev.target.closest && ev.target.closest('[data-act="logout"]');
  if (!b) return;
  const n = (await OB.all()).length;
  if (n && !confirm(`Es ${n === 1 ? "wartet 1 Änderung" : "warten " + n + " Änderungen"}, die nur auf diesem Gerät liegen und noch nicht hochgeladen sind. Beim Abmelden bleiben sie hier gespeichert, werden aber erst nach erneuter Anmeldung hochgeladen. Trotzdem abmelden?`)) return;
  ev.preventDefault(); store.set(TOKEN_KEY, ""); S.login = ""; S.owner = ""; S.lib = null; S.book = null; S.files.clear(); S.msg = null; show("connect");
});
window.addEventListener("online", () => { NET.online = true; netProbe(); });
window.addEventListener("offline", () => { NET.online = false; netProbe(); });
document.addEventListener("visibilitychange", () => { if (!document.hidden && NET.github !== true) netProbe(); });
if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) navigator.serviceWorker.register("sw.js").catch(() => {});
show("connect");
obRender();
netProbe().then(ok => { if (ok) GW_PORTS.outbox.flush(); });
