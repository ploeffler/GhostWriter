/* ---------- Ereignisse ---------- */
document.addEventListener("click", async ev => {
  const t = ev.target.closest("button"); if (!t) return;
  if (t.id === "home"){ S.owner = ""; S.lib = null; S.book = null; S.sec = null; S.chap = null; S.msg = null; return show("connect"); }
  const d = t.dataset;
  if (d.go === "library"){ S.msg = null; show("library"); }
  else if (d.go === "project"){ S.msg = null; show("project"); }
  else if (d.go === "chapter"){ S.msg = null; show("chapter", S.chap); }
  else if (d.go === "back") show(S.report.from, S.report.arg);
  else if (d.report){ const from = S.view, arg = from === "section" ? S.sec.id : S.chap; busy("Bericht wird geladen …"); try { S.report = {path:d.report, text:(await getFile(d.report, S.readRef)).text, from, arg}; show("report"); } catch (e) { S.msg = {kind:"err", html:"Bericht nicht gefunden: " + esc(d.report)}; show(from, arg); } }
  else if (d.act === "review"){ S.msg = null; show("review", d.f); }
  else if (d.act === "queue"){ S.msg = null; show("queue"); }
  else if (d.act === "checkin"){ S.msg = null; show("checkin", d.f); }
  else if (d.act === "reviewapply") reviewApply({file:d.f});
  else if (d.act === "gering"){ S.reviewChain = (S.reviewChain || Promise.resolve()).then(async () => { try { const work = await prepareWork(); S.readRef = work; const {text, data} = await reviewLoad(d.f); await reviewGroup(d.f, text, data, "", "nein", true); } catch (e) { flash("err", "<b>Nicht gespeichert.</b> " + esc(errText(e))); } }); }
  else if (d.act === "gering-show"){ S.reviewGering = true; show("review", d.f); }
  else if (d.act === "all-show"){ S.reviewAll = !S.reviewAll; show("review", d.f); }
  else if (d.act === "allchecks"){ S.showAll = !S.showAll; show("project"); }
  else if (d.act === "copy"){ try { await navigator.clipboard.writeText($("cpy").textContent); t.textContent = "Kopiert"; } catch (e) { t.textContent = "Kopieren nicht möglich – Text markieren"; } }
  else if (d.q) chat((QUICK[scopeOf()] || {})[d.q] || d.q, d.q);
  else if (d.act === "run"){ let a; try { a = JSON.parse(d.a); } catch (e) { return; } const label = a.label; delete a.label; act({action:a.action, data:a, text:label}); }
  else if (d.act === "saverun") saveRun(+d.i);
  else if (d.act === "webres") webResearch(d.s);
  else if (d.act === "webreslow") webResearch(d.s, true);
  else if (d.act === "webcheck") webCheck(d.s);
  else if (d.act === "webcancel"){ S.msg = null; show("section", d.s); }
  else if (d.act === "offres"){ S.msg = null; runStart({section_id:d.s, task:"research", mode:"immediate", offline:true}); }
  else if (d.act === "apply"){ const p = PROPOSAL.exec(S.chat[+d.i].content), el = $("gw-ms"); if (p && el){ el.value = p[1].trim(); el.dispatchEvent(new Event("input", {bubbles:true})); el.scrollIntoView({behavior:"smooth", block:"center"}); } }
});
document.addEventListener("submit", ev => {
  if (ev.target.id === "fConnect"){ ev.preventDefault(); loadRepo($("repoIn").value); }
  if (ev.target.id === "fAsk"){ ev.preventDefault(); const el = $("askIn"), q = el.value; el.value = ""; chat(q); }
});
document.addEventListener("keydown", ev => { if (ev.target.id === "askIn" && ev.key === "Enter" && !ev.shiftKey && !ev.isComposing){ ev.preventDefault(); $("fAsk").requestSubmit(); } });

