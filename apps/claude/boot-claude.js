show("connect");
(async () => {
  const use = n => (window.claude && typeof window.claude.use === "function") ? window.claude.use(n).catch(() => null) : Promise.resolve(null);
  const [m, s] = await Promise.all([use("mcp"), use("sample")]);
  S.mcp = m; S.sample = s; S.ready = true;
  if (S.view === "connect") show("connect");
})();
