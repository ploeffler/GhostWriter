/* ---------- Dreiwege-Vergleich je Absatz (#662, Konfliktlösung) ----------
   merge3(Ausgangstext, lokal, GitHub) → Stücke: Text, der feststeht, oder {conflict:{base, local, remote}} (jeweils Absätze). Absätze sind durch genau
   eine Leerzeile getrennt ("\n\n"), damit Zusammenfügen den Text unverändert wiedergibt. Änderungen an verschiedenen Absätzen werden übernommen,
   gleiche Änderung auf beiden Seiten einmal; nur wo beide Seiten denselben Bereich verschieden geändert haben, bleibt ein Konflikt. */
function m3Paras(t){ return String(t).split("\n\n"); }
function m3Lcs(x, y){
  const n = x.length, m = y.length, dp = Array.from({length:n + 1}, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = x[i] === y[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out = new Map(); let i = 0, j = 0;
  while (i < n && j < m){ if (x[i] === y[j]){ out.set(i, j); i++; j++; } else if (dp[i + 1][j] >= dp[i][j + 1]) i++; else j++; }
  return out;
}
const m3Eq = (p, q) => p.length === q.length && p.every((v, i) => v === q[i]);
function merge3(base, local, remote){
  const B = m3Paras(base), A = m3Paras(local), R = m3Paras(remote), ma = m3Lcs(B, A), mr = m3Lcs(B, R), out = [];
  let pb = 0, pa = 0, pr = 0;
  const region = (eb, ea, er) => {
    const b = B.slice(pb, eb), a = A.slice(pa, ea), r = R.slice(pr, er);
    if (m3Eq(a, b)) out.push(...r); else if (m3Eq(r, b) || m3Eq(a, r)) out.push(...a); else out.push({conflict:{base:b, local:a, remote:r}});
  };
  for (let i = 0; i < B.length; i++){
    if (!ma.has(i) || !mr.has(i)) continue;
    region(i, ma.get(i), mr.get(i)); out.push(B[i]); pb = i + 1; pa = ma.get(i) + 1; pr = mr.get(i) + 1;
  }
  region(B.length, A.length, R.length);
  return out;
}
const m3Conflicts = chunks => chunks.filter(c => typeof c !== "string" && c.conflict).length;
/* Auswahl je Konflikt: "local" | "remote" | "both" (beide untereinander, mit Marke) | Text von Hand */
function m3Join(chunks, choice){
  const mark = (c, k) => `[KONFLIKT PRÜFEN: Fassung ${k === "local" ? "von diesem Gerät" : "von GitHub"}]`;
  const out = []; let n = 0;
  chunks.forEach(c => {
    if (typeof c === "string"){ out.push(c); return; }
    const x = c.conflict, pick = choice[n++];
    if (pick === "local") out.push(...x.local);
    else if (pick === "remote") out.push(...x.remote);
    else if (pick === "both") out.push(mark(x, "local"), ...x.local, mark(x, "remote"), ...x.remote);
    else if (typeof pick === "string") out.push(pick);
    else throw new Error("Konflikt " + n + " ist nicht entschieden");
  });
  return out.join("\n\n");
}
