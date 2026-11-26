const GH = "github";
const EDITORIAL = ["structure","language","proofreading","story_memory","quality_correction"];
const LABEL = {structure:["Struktur","S"],language:["Sprache","L"],proofreading:["Korrektur","K"],story_memory:["Gedächtnis","G"],quality_correction:["Qualität","Q"]};
const KIND_LONG = {structure:"Strukturlektorat",language:"Sprachlektorat",proofreading:"Schlusskorrektur",story_memory:"Buchgedächtnis",quality_correction:"Qualitätsprüfung"};
const ANA = {characters:"Figuren",summaries:"Kurzbeschreibungen",style:"Stil",places:"Schauplätze",timeline:"Zeitleiste",continuity:"Widersprüche",language:"Sprache",chronology:"Chronologie"};
const ANA_SHORT = {characters:"AF",summaries:"AK",style:"ASt",places:"AO",timeline:"AZ",continuity:"AW",language:"ASp",chronology:"AC"};
const MARK = {passed:"✓",passed_with_notes:"✓·",failed:"✗",incomplete:"…",unknown:"?"};
const RES = {passed:"bestanden",passed_with_notes:"bestanden mit Hinweisen",failed:"nicht bestanden",incomplete:"unvollständig",unknown:"Ergebnis unbekannt"};
const STATE = {current:"aktuell",changed:"seit Prüfung geändert",unknown:"Stand unbekannt"};
const LEGEND = "Prüfungen: S Struktur · L Sprache · K Korrektur · G Gedächtnis · Q Qualität · A… Analyse · ✓ bestanden · ✓· mit Hinweisen · ✗ nicht bestanden · … unvollständig · * seit Prüfung geändert · ? Stand bzw. Ergebnis unbekannt.";
const LEGEND_LATEST = LEGEND + " Ein Tag zeigt nur die neueste Prüfung je Art. Ein Tag ist keine Freigabe.";
const LEGEND_FULL = LEGEND + " Ein Tag zeigt nur die neueste Prüfung je Art; frühere stehen unter „Frühere Prüfungen“. Ein Tag ist keine Freigabe.";
const MK = {"PLATZHALTER-ANEKDOTE":"anekdote","QUELLE PRÜFEN":"quelle","MEDIZIN PRÜFEN":"medizin","RECHT PRÜFEN":"recht","KONTINUITÄT PRÜFEN":"kontinuitaet"};
const MK_LABEL = {anekdote:"Platzhalter-Anekdote",quelle:"Quelle prüfen",medizin:"Medizin prüfen",recht:"Recht prüfen",kontinuitaet:"Kontinuität prüfen"};
const MARKER_RE = /\[(PLATZHALTER-ANEKDOTE|QUELLE PRÜFEN|MEDIZIN PRÜFEN|RECHT PRÜFEN|KONTINUITÄT PRÜFEN)(?::\s*([^\]]*))?\]/g;

const S = {mcp:null, sample:null, ready:false, owner:"", repo:"", lib:null, book:null, idx:null, cfg:{}, readRef:"", head:"", pr:null, checks:[], files:new Map(), view:"", sec:null, secNo:"", secFile:null, chap:null, msg:null, chat:[], busy:false, report:null, showAll:false, rules:"", webJobs:{}};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const store = {get(k){try{return localStorage.getItem(k)}catch(e){return null}}, set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const deDate = iso => { const m = /(\d{4})-(\d{2})-(\d{2})/.exec(iso || ""); return m ? `${m[3]}.${m[2]}.${m[1]}` : ""; };
const rankOf = (e, i) => whenOf(e) + "|" + String(i).padStart(6, "0");

