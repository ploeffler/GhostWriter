async function getFile(path, ref, fresh){
  const key = (ref || "") + "|" + path;
  if (!fresh && S.files.has(key)) return S.files.get(key);
  const f = await GW_PORTS.git.getFile(path, ref);
  if (f.text === null) throw {message:"Datei nicht lesbar: " + path};
  S.files.set(key, f);
  return f;
}
async function pool(items, n, fn){ const out = new Array(items.length); let i = 0; await Promise.all(Array.from({length:Math.min(n, items.length)}, async () => { while (i < items.length){ const k = i++; try { out[k] = await fn(items[k]); } catch (e) { out[k] = null; } } })); return out; }
const workOf = b => b.work_branch || "ghostwriter/" + b.branch;
async function openPR(b){
  const p = (await GW_PORTS.git.listPRs({head:workOf(b), base:b.branch}))[0] || null;
  return p ? {number:p.number, url:p.html_url, head:p.head && p.head.sha} : null;
}
async function prCommits(pr){
  try { pr.list = await GW_PORTS.git.prCommits(pr.number); pr.commits = pr.list.length || 1; } catch (e) { pr.list = []; pr.commits = 1; }
  return pr;
}

