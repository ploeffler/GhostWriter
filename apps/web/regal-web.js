/* ---------- Bücherregal: Serien als Akkordeon (#662) ----------
   Das Widget „Bücherregal“ setzt über die Karten einer Serie eine Überschrift. Diese App macht daraus ein Akkordeon: je Serie (und „Einzelne Bücher“) ein
   aufklappbarer Bereich mit Titel, Zahl der Bände, Fortschritt aller Bände und „Serie öffnen ›“; darin liegen die Karten wieder im Raster. Der Zustand (auf/zu)
   wird je Serie im Browser gemerkt. Serien sind zuerst zu, „Einzelne Bücher“ zuerst offen. Ohne Serien bleibt das Regal unverändert. Die Karten behalten ihre Funktion. */
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
  const shelf = root.querySelector && root.querySelector(".gw-shelf"); if (!shelf || shelf.dataset.acc) return;
  const kids = [...shelf.children]; if (!kids.some(k => k.classList.contains("gw-sh"))) return;
  const groups = []; let cur = null;
  kids.forEach(k => { if (k.classList.contains("gw-sh")){ cur = {head:k, cards:[]}; groups.push(cur); } else if (cur) cur.cards.push(k); });
  shelf.dataset.acc = "1"; shelf.style.display = "block"; shelf.textContent = "";
  groups.forEach(g => shelf.appendChild(regalGroup(g)));
}
{ const prev = GW_PORTS.afterRender; GW_PORTS.afterRender = (name, root) => { if (prev) prev(name, root); if (name === "buecherregal") regalPatch(root); }; }
