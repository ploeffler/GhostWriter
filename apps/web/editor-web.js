/* EasyMDE für das Manuskriptfeld; ?editor=text verwendet das einfache Textfeld.
   Speichern und Freigaben bleiben bei GhostWriter. Keine eigenen Entwürfe im localStorage. */
const GW_EDITOR = {enabled:new URLSearchParams(location.search).get("editor") !== "text", assets:null, active:null};
function editorAssets(){
  if (GW_EDITOR.assets) return GW_EDITOR.assets;
  const css = document.createElement("link"); css.rel = "stylesheet"; css.href = "vendor/easymde.min.css"; document.head.appendChild(css);
  const script = src => new Promise((resolve, reject) => {
    const s = document.createElement("script"); s.src = src; s.onload = resolve; s.onerror = () => reject(new Error("Editor-Datei nicht verfügbar")); document.head.appendChild(s);
  });
  GW_EDITOR.assets = script("vendor/purify.min.js").then(() => script("vendor/easymde.min.js"));
  return GW_EDITOR.assets;
}
function editorRelease(){
  const a = GW_EDITOR.active; if (!a) return;
  a.observer.disconnect(); a.editor.toTextArea(); a.note.remove(); GW_EDITOR.active = null;
}
function editorPreview(markdown){
  // Kein fremdes Bild laden; GhostWriter-Bildverweise bleiben im Manuskript unverändert.
  const safe = window.DOMPurify.sanitize(window.EasyMDE.prototype.markdown.call({options:{}}, markdown), {
    ALLOWED_TAGS:["p", "br", "strong", "em", "del", "blockquote", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "pre", "code", "a", "table", "thead", "tbody", "tr", "th", "td"],
    ALLOWED_ATTR:["href", "title"], ALLOW_DATA_ATTR:false
  });
  const view = document.createElement("template"); view.innerHTML = safe;
  view.content.querySelectorAll("a[href]").forEach(a => { a.target = "_blank"; a.rel = "noopener noreferrer"; });
  return view.innerHTML;
}
async function editorAttach(name, root){
  editorRelease();
  if (!GW_EDITOR.enabled || name !== "abschnitt-bearbeiten") return;
  const area = root.querySelector("#gw-ms"); if (!area) return;
  try { await editorAssets(); } catch (_) {
    if (area.isConnected){ const n = document.createElement("p"); n.textContent = "Editor nicht verfügbar; das normale Textfeld bleibt benutzbar."; area.before(n); }
    return;
  }
  if (!area.isConnected || GW_EDITOR.active) return; // inzwischen in einen anderen Abschnitt gewechselt
  const E = window.EasyMDE;
  const tools = [["bold", E.toggleBold, "Fett"], ["italic", E.toggleItalic, "Kursiv"],
    ["unordered-list", E.toggleUnorderedList, "Liste"], ["preview", E.togglePreview, "Vorschau"],
    ["fullscreen", E.toggleFullScreen, "Vollbild"]];
  const editor = new E({element:area, forceSync:true, autoDownloadFontAwesome:false, spellChecker:false,
    autosave:{enabled:false}, status:false, uploadImage:false, minHeight:"320px", tabSize:2,
    toolbar:tools.map(([name, action, title]) => ({name, action, className:"gw-editor-tool", title, icon:title})),
    previewRender:editorPreview});
  const note = document.createElement("p"); note.className = "dim gw-editor-note";
  note.textContent = "Markdown-Editor · Vorschau ohne Bilder; kein Buchsatz.";
  editor.codemirror.getWrapperElement().parentNode.before(note);
  let syncing = false;
  editor.codemirror.on("change", () => {
    if (syncing) return; area.value = editor.value(); area.dispatchEvent(new Event("input", {bubbles:true}));
  });
  area.addEventListener("input", () => {
    if (area.value !== editor.value()){ syncing = true; editor.value(area.value); syncing = false; }
  });
  let locked;
  const syncLock = () => {
    const next = area.disabled || area.readOnly || !!area.closest(".locked") ||
      (typeof roleWhy === "function" && !!roleWhy("section.update"));
    if (next === locked) return; locked = next; editor.codemirror.setOption("readOnly", next ? "nocursor" : false);
    editor.gui.toolbar.querySelectorAll("button").forEach(b => { b.disabled = next; });
  };
  const observer = new MutationObserver(syncLock); observer.observe(root, {subtree:true, attributes:true, attributeFilter:["disabled", "readonly", "class"]});
  GW_EDITOR.active = {area, editor, observer, note}; syncLock();
}
{ const previous = GW_PORTS.afterRender; GW_PORTS.afterRender = (name, root) => {
  if (previous) previous(name, root); editorAttach(name, root);
}; }
