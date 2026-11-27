/* ---------- Bücherregal: Karten aufgeräumt, Auflagen als Akkordeon, Serien als Akkordeon (#662) ----------
   Karten: „eingerichtet“ und der Branch stehen nicht mehr auf der Karte („im Aufbau“ bleibt). Unter jeder Karte klappt „Auflagen und Vorabfassungen“ auf:
   Links zu den erzeugten Auflagen (aus library.json, Release-Seite auf GitHub) und zu den Vorabfassungen (Pre-Releases des Repositorys, einmal gelesen). Ohne Einträge fehlt das Akkordeon.
   Das Widget „Bücherregal“ setzt über die Karten einer Serie eine Überschrift. Diese App macht daraus ein Akkordeon: je Serie (und „Einzelne Bücher“) ein
   aufklappbarer Bereich mit Titel, Zahl der Bände, Fortschritt aller Bände und „Serie öffnen ›“; darin liegen die Karten wieder im Raster. Der Zustand (auf/zu)
   wird je Serie im Browser gemerkt. Serien sind zuerst zu, „Einzelne Bücher“ zuerst offen. Ohne Serien bleibt das Regal unverändert. Die Karten behalten ihre Funktion. */
const REL_ALL = {p:null};
const regalReleases = () => REL_ALL.p || (REL_ALL.p = Promise.resolve().then(() => GW_PORTS.git.listReleases(30)).catch(() => []));
const regalRelUrl = tag => `https://github.com/${S.owner}/${S.repo}/releases/tag/${encodeURIComponent(tag)}`;
function regalLinks(b, rels){   // Auflagen aus library.json (Tag → Release-Seite), dazu Vorabfassungen aus den Pre-Releases dieses Buchs
  const items = (b.editions || []).map(e => { const n = e && typeof e === "object" ? (e.number || e.edition) : e; if (!n) return null; const tag = (e && e.tag) || "";
    return {text:"Auflage " + n, date:deDate((e && (e.date || e.published)) || ""), url:tag ? regalRelUrl(tag) : "", tag}; }).filter(Boolean);
  const known = new Set(items.map(x => x.tag).filter(Boolean));
  (rels || []).filter(r => r.pre && r.tag && !known.has(r.tag) && runRelOfBook(r, b)).forEach(r => items.push({text:(r.name || r.tag) + " (Vorabfassung)", date:deDate(String(r.date || "")), url:r.url || regalRelUrl(r.tag), tag:r.tag}));
  return items;
}
function regalAccFill(d, b, rels){
  const items = regalLinks(b, rels); d.hidden = !items.length; if (!items.length) return;
  d.querySelector(".gw-ednum").textContent = " (" + items.length + ")";
  d.querySelector(".gw-edlist").innerHTML = items.map(x => `<li>${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.text)}</a>` : esc(x.text)}${x.date ? ` <span class="dim">${esc(x.date)}</span>` : ""}</li>`).join("");
}
function regalTidy(card){
  if (card.dataset.tidy) return; card.dataset.tidy = "1";
  const bk = card.querySelector(".gw-book"); if (!bk) return;
  if (bk.dataset.state === "ready"){ const b = bk.querySelector(".st > b"); if (b){ const st = b.parentNode; b.remove(); const t = st.firstChild; if (t && t.nodeType === 3) t.textContent = t.textContent.replace(/^\s*·\s*/, ""); } }
  bk.querySelectorAll(".st code").forEach(c => { const st = c.parentNode; c.remove(); st.textContent = st.textContent.replace(/\s*·\s*$/, "").trim(); if (!st.textContent) st.remove(); });
  const b = ((S.lib && S.lib.books) || []).find(x => x.branch === bk.dataset.branch); if (!b) return;
  const d = document.createElement("details"); d.className = "gw-acc gw-eds2";
  d.innerHTML = '<summary><span class="gw-acct">Auflagen und Vorabfassungen<span class="gw-ednum"></span></span></summary><ul class="gw-edlist"></ul>';
  card.appendChild(d); regalAccFill(d, b, null);
  regalReleases().then(rels => { if (d.isConnected) regalAccFill(d, b, rels); });
}
function regalSums(cards){
  let done = 0, total = 0;
  cards.forEach(c => { const m = /(\d+)\s+von\s+(\d+)\s+Abschnitt/.exec([...c.querySelectorAll(".st")].map(x => x.textContent).join(" ")); if (m){ done += +m[1]; total += +m[2]; } });
  return {done, total, pct:total ? Math.round(100 * done / total) : 0};
}
function regalGroup(g){
  const series = !g.head.classList.contains("plain"), cards = g.cards.filter(c => c.classList.contains("gw-card")), first = cards[0] && cards[0].querySelector(".gw-book");
  const title = (g.head.querySelector("span") || {}).textContent || "", sid = series ? ((first && first.dataset.series) || title) : "einzeln", key = "gw.acc." + sid;
  const sum = regalSums(cards), vols = cards.length, d = document.createElement("details");
  d.className = "gw-acc"; d.dataset.series = series ? sid : "";
  const saved = store.get(key);
  d.open = saved == null ? !series : saved === "1";
  const prog = series && sum.total ? `<span class="gw-accbar" title="${sum.done} von ${sum.total} Abschnitten freigegeben"><i style="width:${sum.pct}%"></i></span>` : "";
  d.innerHTML = `<summary><span class="gw-acct">${esc(title)}</span><span class="gw-accm">${vols === 1 ? "1 Buch" : vols + (series ? " Bände" : " Bücher")}${series && sum.total ? ` · ${sum.done} von ${sum.total} Abschnitten freigegeben` : ""}</span>${prog}${series ? '<button type="button" class="link gw-accopen">Serie öffnen ›</button>' : ""}</summary>`;
  const body = document.createElement("div"); body.className = "gw-shelf"; cards.forEach(c => body.appendChild(c)); d.appendChild(body);
  const btn = d.querySelector(".gw-accopen"); if (btn) btn.addEventListener("click", ev => { ev.preventDefault(); ev.stopPropagation(); g.head.click(); });
  d.addEventListener("toggle", () => store.set(key, d.open ? "1" : "0"));
  return d;
}
function regalPatch(root){
  const shelf = root.querySelector && root.querySelector(".gw-shelf"); if (!shelf) return;
  shelf.querySelectorAll(".gw-card").forEach(regalTidy);
  if (shelf.dataset.acc) return;
  const kids = [...shelf.children]; if (!kids.some(k => k.classList.contains("gw-sh"))) return;
  const groups = []; let cur = null;
  kids.forEach(k => { if (k.classList.contains("gw-sh")){ cur = {head:k, cards:[]}; groups.push(cur); } else if (cur) cur.cards.push(k); });
  shelf.dataset.acc = "1"; shelf.style.display = "block"; shelf.textContent = "";
  groups.forEach(g => shelf.appendChild(regalGroup(g)));
}
{ const prev = GW_PORTS.afterRender; GW_PORTS.afterRender = (name, root) => { if (prev) prev(name, root); if (name === "buecherregal") regalPatch(root); }; }
