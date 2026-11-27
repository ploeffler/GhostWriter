// Outbox der eigenen Web-App (#662, #61): lokal sichern, später hochladen, bei Konflikt nichts überschreiben. Aufruf: node apps/web/tests/outbox.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "outbox-web.js"), "utf8");

function load(opts){
  opts = opts || {};
  const els = {unsaved:{hidden:true, className:"", textContent:"", innerHTML:""}, net:{hidden:true, className:"", textContent:""}};
  const pushes = [], prs = [], remote = opts.remote || {}, listeners = {};
  const ctx = {
    NET: {online:true, github:true}, S: {owner:"o", repo:"r", book:{branch:"b"}, view:"project"}, token: () => "tok", esc: s => String(s), $: id => els[id],
    chapters: () => [{sections:[{path:"chapters/01/a.md", title:"Eins"}]}], errText: e => "Fehler: " + e.message,
    document: {title:"GhostWriter"}, window: {addEventListener: (t, f) => { listeners[t] = f; }}, navigator: {}, setTimeout, Date, Promise, JSON, Array, Set, Map, Object, String,
    GW_PORTS: {agent:"Web", git: {pushFiles: async (b, f, m, a) => { if (opts.pushError) throw opts.pushError; pushes.push({b, f, m, a}); }, createPR: async p => { prs.push(p); }}},
    prepareWork: async b => "ghostwriter/" + b.branch, getFile: async (p, ref) => { if (remote[p] === undefined) throw {message:"404"}; return remote[p]; },
    openPR: async () => opts.pr === undefined ? null : opts.pr, loadBookData: async () => {}, show: () => {}
  };
  vm.runInNewContext(src + "\n;this.__x = {OB, obFlush, obRender, obPlace};", ctx);
  return {ctx, x: ctx.__x, els, pushes, prs, listeners};
}
const entry = (o) => Object.assign({repo:"o/r", book:{branch:"b", work_branch:""}, files:[{path:"chapters/01/a.md", content:"lokal"}], message:"M", action:"section.update", seen:{"chapters/01/a.md":"s1"}}, o || {});

(async () => {
  // Hinzufügen: Zähler, Leiste (nicht wegklickbar), Tab-Titel, Ort verständlich
  let t = load({remote:{"chapters/01/a.md":{sha:"s1", text:"alt"}}});
  const P = t.ctx.GW_PORTS.outbox;
  assert.equal(await P.add(entry()), 1);
  assert.equal(t.els.unsaved.hidden, false);
  assert.match(t.els.unsaved.innerHTML, /1 Änderung nur auf diesem Gerät – noch nicht hochgeladen/);
  assert.match(t.els.unsaved.innerHTML, /Jetzt hochladen/);
  assert.match(t.els.unsaved.innerHTML, /Abschnitt 1\.1 „Eins“/);
  assert.equal(t.ctx.document.title, "(1) GhostWriter");
  assert.equal(await P.pending("b"), true); assert.equal(await P.pending("anderes"), false);
  assert.equal(JSON.stringify(await P.overlay("b")), JSON.stringify([{path:"chapters/01/a.md", content:"lokal"}]));
  // Offline: kein Knopf, Hinweis; Verlassen fragt (beforeunload)
  t.ctx.NET.online = false; await t.x.obRender();
  assert.match(t.els.unsaved.innerHTML, /Hochladen, sobald wieder Netz da ist/); assert.doesNotMatch(t.els.unsaved.innerHTML, /Jetzt hochladen/);
  let ev = {prevented:false, preventDefault() { this.prevented = true; }}; t.listeners.beforeunload(ev); assert.equal(ev.prevented, true);
  await P.flush(); assert.equal(t.pushes.length, 0, "offline wird nichts hochgeladen");
  // Wieder online: unverändert auf GitHub → hochladen, Eintrag weg, PR angelegt, Leiste weg
  t.ctx.NET.online = true; await P.flush();
  assert.equal(t.pushes.length, 1); assert.equal(t.pushes[0].b, "ghostwriter/b"); assert.equal(t.pushes[0].m, "M"); assert.equal(t.pushes[0].a, "section.update");
  assert.equal(t.prs.length, 1); assert.equal((await P.list()).length, 0); assert.equal(t.els.unsaved.hidden, true); assert.equal(t.ctx.document.title, "GhostWriter");
  ev = {prevented:false, preventDefault() { this.prevented = true; }}; t.listeners.beforeunload(ev); assert.equal(ev.prevented, false);

  // Konflikt: Datei auf GitHub inzwischen geändert → nichts überschrieben, Eintrag bleibt, spätere Einträge am selben Buch warten
  t = load({remote:{"chapters/01/a.md":{sha:"s2", text:"andere Fassung"}}});
  await t.ctx.GW_PORTS.outbox.add(entry()); await t.ctx.GW_PORTS.outbox.add(entry({files:[{path:"chapters/01/neu.md", content:"x"}], seen:{}}));
  await t.ctx.GW_PORTS.outbox.flush();
  assert.equal(t.pushes.length, 0, "bei Konflikt wird nichts hochgeladen");
  const left = await t.ctx.GW_PORTS.outbox.list(); assert.equal(left.length, 2); assert.equal(left[0].state, "konflikt"); assert.equal(left[1].state, "wartet");
  assert.match(t.els.unsaved.innerHTML, /1 Konflikt/); assert.match(t.els.unsaved.innerHTML, /nichts wurde überschrieben/);

  // Schon identisch auf GitHub (etwa nach unklarem Fehler): kein doppelter Commit, Eintrag verschwindet
  t = load({remote:{"chapters/01/a.md":{sha:"s9", text:"lokal"}}});
  await t.ctx.GW_PORTS.outbox.add(entry()); await t.ctx.GW_PORTS.outbox.flush();
  assert.equal(t.pushes.length, 0); assert.equal((await t.ctx.GW_PORTS.outbox.list()).length, 0);

  // Netzfehler beim Hochladen: Eintrag bleibt unverändert liegen (später erneut); anderer Fehler: als Fehler markiert, nichts geht verloren
  t = load({remote:{"chapters/01/a.md":{sha:"s1", text:"alt"}}, pushError:{code:"offline", message:"x"}});
  await t.ctx.GW_PORTS.outbox.add(entry()); await t.ctx.GW_PORTS.outbox.flush();
  assert.equal((await t.ctx.GW_PORTS.outbox.list())[0].state, "wartet");
  t = load({remote:{"chapters/01/a.md":{sha:"s1", text:"alt"}}, pushError:{code:"http_403", message:"verboten"}});
  await t.ctx.GW_PORTS.outbox.add(entry()); await t.ctx.GW_PORTS.outbox.flush();
  const f = (await t.ctx.GW_PORTS.outbox.list())[0]; assert.equal(f.state, "fehler"); assert.match(f.error, /verboten/); assert.match(t.els.unsaved.innerHTML, /nicht hochgeladen/);

  // Anderes Repository ist geöffnet: Einträge fremder Repositorys werden nicht angefasst
  t = load({remote:{"chapters/01/a.md":{sha:"s1", text:"alt"}}});
  await t.ctx.GW_PORTS.outbox.add(entry({repo:"x/y"})); await t.ctx.GW_PORTS.outbox.flush();
  assert.equal(t.pushes.length, 0); assert.equal(await t.ctx.GW_PORTS.outbox.pending(), false);   // gehört nicht zu o/r
  // Älter als 24 Stunden: Erinnerung
  t = load(); await t.ctx.GW_PORTS.outbox.add(entry()); const old = (await t.x.OB.all())[0]; old.created = Date.now() - 25 * 3600 * 1000; await t.x.OB.put(old); await t.x.obRender();
  assert.match(t.els.unsaved.innerHTML, /mehr als 24 Stunden/);
  // Ohne dauerhaften Speicher (Rückfall im Arbeitsspeicher) wird gewarnt
  assert.match(t.els.unsaved.innerHTML, /keinen dauerhaften Speicher/);
  console.log("outbox ok");
})().catch(e => { console.error(e); process.exit(1); });
