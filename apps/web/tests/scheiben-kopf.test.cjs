// Regressionstest für fehlende Scheiben-Platzhalter (#775).
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../../shared/s06-darstellung.js"), "utf8");
const root = { innerHTML: "", querySelectorAll: () => [] };
const calls = [];
const context = {
  window: { GW: { render: (name, data, target, language) => calls.push({ name, data, target, language }) } },
  GW_PORTS: {},
  $: () => root,
  NodeFilter: { SHOW_TEXT: 4 },
  document: { createTreeWalker: () => ({ nextNode: () => null }) },
  esc: String,
  Promise, Set, Array, Object, String, JSON, RegExp
};

vm.runInNewContext(source, context);
context.gwRender("buecherregal", { BOOKS: [] });
assert.equal(calls[0].data.SLICE, "");
assert.equal(calls[0].name, "buecherregal");

context.gwRender("projektuebersicht", { SLICE: "buch", TITLE: "Test" });
assert.equal(calls[1].data.SLICE, "buch");
assert.equal(calls[1].data.TITLE, "Test");

context.gwRender("kapitelansicht", { SLICE: null });
assert.equal(calls[2].data.SLICE, "");

console.log("scheiben-kopf ok");
