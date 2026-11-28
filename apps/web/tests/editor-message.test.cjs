// Nachrichtenvertrag: echte UI-Laufzeit -> Nachrichtenleser der App, ohne Datenverlust.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../../..'), ctx={window:{},setTimeout,console};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root,'apps/web/vendor/gw-lite.js'),'utf8'),ctx);ctx.GW=ctx.window.GW;
vm.runInContext(fs.readFileSync(path.join(root,'apps/shared/s08-aktionen.js'),'utf8')+'\nthis.parse=parseAction;',ctx);
const value={section_id:'sec-1',goal:'',summary:'  Anfang mit Leerraum',fact_check:'disabled',
 manuscript:'**Fett**, *kursiv*, `Code`, \\Pfad und \\`maskiert`.\n\n  Einzug\nLetzte Zeile. ![](bild:img-1)',characters:['char-a','char-b'],flag:false,weight:0};
const text=ctx.GW.message('Abschnitt speichern','section.update',value), got=ctx.parse(text);
assert.equal(got.action,'section.update');assert.deepEqual(JSON.parse(JSON.stringify(got.data)),value);
assert.equal(ctx.parse('Speichern\n\n```gw\n{"action":"section.update","manuscript":"alt"}\n```').data.manuscript,'alt');
assert.equal(ctx.parse('`gw:view.section section_id=sec-1`').data.section_id,'sec-1');
assert.equal(ctx.parse('`gw:section.update`\ncharacters (JSON): [kaputt').action,'');
assert.equal(Object.getPrototypeOf(ctx.parse('`gw:section.update`\n__proto__ (JSON): {"polluted":true}').data),null);
assert.equal({}.polluted,undefined);
console.log('editor-message: ok');
