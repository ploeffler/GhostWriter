// Anschluss der eigenen Web-App (#662): GitHub-REST mit Token, ohne Netz (fetch ist nachgestellt). Aufruf: node apps/web/tests/ports-web.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "ports-web.js"), "utf8");

function load(handler, token){
  const calls = [], mem = {"gw.token": token === undefined ? "tok" : token};
  const ctx = {
    S: {owner:"o", repo:"r"}, store: {get:k => mem[k] || null, set:(k, v) => { mem[k] = v; }}, esc: s => String(s), $: () => null, msgBox: () => "",
    atob: s => Buffer.from(s, "base64").toString("binary"), TextDecoder, Uint8Array, Date, Promise, Map, encodeURIComponent, JSON, Array, String, Object,
    fetch: async (url, opt) => { calls.push({url, method:opt.method, headers:opt.headers, body:opt.body ? JSON.parse(opt.body) : null}); return handler(url, opt, calls); }
  };
  vm.runInNewContext(src + "\n;this.__x = {GW_PORTS, errText, rest, token};", ctx);
  return {x: ctx.__x, calls, mem};
}
const res = (status, body, text) => ({ok: status < 400, status, statusText: "S" + status, text: async () => text !== undefined ? text : JSON.stringify(body)});
const b64 = s => Buffer.from(s, "utf8").toString("base64");

(async () => {
  // 1. Ohne Token: kein Netzzugriff
  let t = load(() => res(200, {}), "");
  await assert.rejects(t.x.GW_PORTS.git.me(), e => e.code === "no_token");
  assert.equal(t.calls.length, 0);

  // 2. getFile: UTF-8, Blob-Kennung und Commit der Referenz; Token nur an api.github.com
  t = load(url => /\/commits\//.test(url) ? res(200, null, "abc123\n") : res(200, {type:"file", encoding:"base64", content:b64("Grüße\nzweite Zeile"), sha:"blob1"}));
  let f = await t.x.GW_PORTS.git.getFile("chapters/ü/a b.md", "buch/x");
  assert.deepEqual({text:f.text, sha:f.sha, commit:f.commit}, {text:"Grüße\nzweite Zeile", sha:"blob1", commit:"abc123"});
  assert(t.calls.some(c => c.url === "https://api.github.com/repos/o/r/contents/chapters/%C3%BC/a%20b.md?ref=buch%2Fx"));
  assert(t.calls.some(c => c.url === "https://api.github.com/repos/o/r/commits/buch/x" && c.headers.Accept === "application/vnd.github.sha"));
  assert(t.calls.every(c => c.url.startsWith("https://api.github.com/") && c.headers.Authorization === "Bearer tok"));
  // Commit-Kennung wird kurz gemerkt: zweite Datei derselben Referenz fragt sie nicht noch einmal ab
  const before = t.calls.filter(c => /\/commits\//.test(c.url)).length;
  await t.x.GW_PORTS.git.getFile("b.md", "buch/x");
  assert.equal(t.calls.filter(c => /\/commits\//.test(c.url)).length, before);

  // 3. Fehlerabbildung
  t = load(() => res(404, {message:"Not Found"}));
  await assert.rejects(t.x.GW_PORTS.git.getFile("x", "main"), e => e.code === "http_404");
  t = load(() => { throw new TypeError("offline"); });
  await assert.rejects(t.x.GW_PORTS.git.me(), e => e.code === "offline");
  t = load(() => res(503, {}));
  await assert.rejects(t.x.GW_PORTS.git.me(), e => e.code === "server_unavailable");
  const E = t.x.errText;
  assert.match(E({code:"http_401"}), /ungültig oder abgelaufen/);
  assert.match(E({code:"http_403", message:"API rate limit exceeded"}), /begrenzt/);
  assert.match(E({code:"http_403", message:"Resource not accessible"}), /Contents/);
  assert.match(E({code:"http_404"}), /owner\/repo/);
  assert.match(E({code:"offline"}), /Keine Verbindung/);

  // 4. Listen: Änderungspakete, Commits (flache Form wie im Konnektor), Verzeichnisse
  t = load(url => /\/pulls\/7\/commits/.test(url) ? res(200, [{sha:"s1", commit:{message:"M", author:{date:"2026-11-26T10:00:00Z", name:"N"}}}])
                  : /\/pulls\?/.test(url) ? res(200, [{number:7}]) : res(200, {message:"Not Found"}));
  assert.equal((await t.x.GW_PORTS.git.listPRs({head:"ghostwriter/b", base:"b"}))[0].number, 7);
  assert(t.calls[0].url.endsWith("/pulls?state=open&per_page=5&head=o%3Aghostwriter%2Fb&base=b"));
  assert.deepEqual(JSON.parse(JSON.stringify((await t.x.GW_PORTS.git.prCommits(7))[0])), {sha:"s1", message:"M", author:{date:"2026-11-26T10:00:00Z", name:"N"}});
  assert.deepEqual(JSON.parse(JSON.stringify(await t.x.GW_PORTS.git.listDir("d"))), []);   // kein Array → leer

  // 5. Schreiben: Blobs, Baum, Commit, Branch ohne Gewalt vorrücken; Kennung in der Nachricht
  t = load((url, opt) => {
    if (/git\/ref\/heads/.test(url)) return res(200, {object:{sha:"h0"}});
    if (/git\/commits\/h0/.test(url)) return res(200, {tree:{sha:"t0"}});
    if (/git\/blobs/.test(url)) return res(201, {sha:"b" + JSON.parse(opt.body).content.length});
    if (/git\/trees/.test(url)) return res(201, {sha:"t1"});
    if (/git\/commits/.test(url)) return res(201, {sha:"c1"});
    return res(200, {});
  });
  await t.x.GW_PORTS.git.pushFiles("ghostwriter/b", [{path:"a.md", content:"Ä"}, {path:"b.yml", content:"x: 1"}], "Abschnitt gespeichert", "section.update");
  const tree = t.calls.find(c => /git\/trees/.test(c.url)).body, commit = t.calls.find(c => /git\/commits$/.test(c.url)).body, patch = t.calls[t.calls.length - 1];
  assert.equal(tree.base_tree, "t0"); assert.equal(tree.tree.length, 2); assert.equal(tree.tree[0].mode, "100644");
  assert.equal(commit.message, "Abschnitt gespeichert\n\nGhostWriter Web-App\nGhostWriter-Aktion: section.update"); assert.deepEqual(JSON.parse(JSON.stringify(commit.parents)), ["h0"]);
  assert.equal(patch.method, "PATCH"); assert(patch.url.endsWith("/git/refs/heads/ghostwriter/b")); assert.equal(patch.body.force, false); assert.equal(patch.body.sha, "c1");
  // Branch inzwischen geändert (422): verständliche Meldung, nichts überschrieben
  t = load((url, opt) => /git\/refs\//.test(url) && opt.method === "PATCH" ? res(422, {message:"Update is not a fast forward"})
         : /git\/ref\/heads/.test(url) ? res(200, {object:{sha:"h0"}}) : /git\/commits\/h0/.test(url) ? res(200, {tree:{sha:"t0"}}) : res(201, {sha:"x"}));
  await assert.rejects(t.x.GW_PORTS.git.pushFiles("w", [{path:"a", content:"b"}], "m"), e => /inzwischen geändert/.test(e.message));

  // 6. Merge, Arbeits-Branch, Änderungspaket
  t = load(url => /git\/ref\/heads/.test(url) ? res(200, {object:{sha:"h0"}}) : res(200, {}));
  await t.x.GW_PORTS.git.createBranch("ghostwriter/b", "b");
  assert.deepEqual(JSON.parse(JSON.stringify(t.calls[1].body)), {ref:"refs/heads/ghostwriter/b", sha:"h0"});
  await t.x.GW_PORTS.git.mergePR(3, {title:"T", expectedHeadSha:"h9"});
  assert.deepEqual(JSON.parse(JSON.stringify(t.calls[2].body)), {merge_method:"merge", commit_title:"T", sha:"h9"});
  await t.x.GW_PORTS.git.createPR({head:"h", base:"b", title:"t", body:"x"});
  assert.equal(t.calls[3].url, "https://api.github.com/repos/o/r/pulls");
  console.log("ports-web ok");
})().catch(e => { console.error(e); process.exit(1); });
