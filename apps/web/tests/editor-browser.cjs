// Optionaler echter Browsertest: GW_TEST_PLAYWRIGHT=/pfad/zu/playwright-core, GW_TEST_BROWSER=/pfad/zu/chrome.
const {chromium} = require(process.env.GW_TEST_PLAYWRIGHT || 'playwright-core');
(async () => {
  const browser = await chromium.launch({executablePath:process.env.GW_TEST_BROWSER, headless:true, args:['--no-sandbox']});
  try {
    for (const width of [1100, 390]){
      const page = await browser.newPage({viewport:{width,height:950}});
      await page.route(/^https?:/, route => route.abort()); // Testdateien lokal, niemals GitHub oder sonstige Dienste aufrufen.
      await page.goto(process.argv[2]);
      await page.waitForFunction(() => /^(PASS:|FAIL:|ERROR:)/.test(document.getElementById('result')?.textContent || ''), null, {timeout:15000});
      const result = await page.locator('#result').innerText();
      if (!result.startsWith('PASS:')) throw Error(width + 'px: ' + result);
      if (width === 390 && await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) throw Error('Schmale Ansicht läuft über');
      if (width === 390) process.stdout.write(await page.content());
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode=1; });
