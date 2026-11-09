/* Local search: no network service, analytics or user data transmission. */
(function (global) {
  'use strict';
  const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  function search(entries, query) {
    const words = normalize(query.trim()).split(/\s+/).filter(Boolean);
    if (!words.length) return [];
    return entries.map(entry => {
      const title = normalize(entry.title), text = normalize(entry.text);
      if (!words.every(word => title.includes(word) || text.includes(word))) return null;
      return {entry, score: words.reduce((sum, word) => sum + (title.includes(word) ? 5 : 1), 0)};
    }).filter(Boolean).sort((a, b) => b.score - a.score).slice(0, 20).map(match => match.entry);
  }
  if (typeof module !== 'undefined') module.exports = {search};
  if (!global.document) return;
  const input = document.querySelector('#search'), results = document.querySelector('#results');
  const status = document.querySelector('#search-status'), lang = document.documentElement.lang;
  let entries, pending;
  async function update() {
    const query = input.value;
    if (!query.trim()) { results.replaceChildren(); status.textContent = ''; return; }
    try {
      pending = pending || fetch('search-index.json').then(response => {
        if (!response.ok) throw new Error('index');
        return response.json();
      }).catch(error => { pending = null; throw error; });
      entries = entries || await pending;
      if (input.value !== query) return;
      const matches = search(entries, query);
      results.replaceChildren();
      for (const match of matches) {
        const item = document.createElement('li'), link = document.createElement('a');
        link.href = match.url; link.textContent = match.title;
        const snippet = document.createElement('small');
        const at = normalize(match.text).indexOf(normalize(query.trim().split(/\s+/)[0]));
        const start = Math.max(0, at - 45);
        snippet.textContent = (start ? '… ' : '') + match.text.slice(start, start + 170) + ' …';
        item.append(link, snippet); results.append(item);
      }
      status.textContent = matches.length ? `${matches.length} ${lang === 'de' ? 'Treffer' : 'results'}` : (lang === 'de' ? 'Keine Treffer.' : 'No results.');
    } catch (_) {
      status.textContent = lang === 'de' ? 'Suche nicht verfügbar. Nutze die Navigation; starte die lokale HTTP-Vorschau statt file://.' : 'Search unavailable. Use navigation; start the local HTTP preview rather than file://.';
    }
  }
  document.querySelector('form[role="search"]').addEventListener('submit', event => { event.preventDefault(); update(); });
  input.addEventListener('input', update);
})(typeof window === 'undefined' ? globalThis : window);
