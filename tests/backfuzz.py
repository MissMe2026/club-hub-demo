"""Random back / forward / sheet / menu sessions. The app's screen and history position must always
match a simple model of Safari's history (v17: history is the single source of truth)."""
import asyncio, random, sys
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
SC = "overview events calendar accounts assistant inbox analytics notifications announcements eventcal eventstats reminders forums messaging whatsapp blog tasks dashboard members team requests resources directory settings search drafts".split()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        bad = 0
        for seed in range(SEEDS):
            r = random.Random(seed)
            pg = await b.new_page(viewport={'width': 390, 'height': 844}); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(URL); await pg.wait_for_timeout(300)
            await pg.locator('.sp-enter >> visible=true').first.click(); await pg.wait_for_timeout(300)
            await pg.locator('.ch-role[data-persona="lead"] >> visible=true').first.click(); await pg.wait_for_timeout(500)
            model, idx = ['overview'], 0
            for step in range(60):
                a = r.random(); did = ''
                if a < 0.40:
                    v = r.choice(SC); cur = await pg.evaluate('S.view')
                    await pg.evaluate(f"go('{v}')"); await pg.wait_for_timeout(80)
                    now = await pg.evaluate('S.view')
                    if now != cur: model = model[:idx + 1] + [now]; idx += 1
                    did = 'go ' + v
                elif a < 0.60:
                    if idx > 0: await pg.go_back(); await pg.wait_for_timeout(250); idx -= 1; did = 'back'
                elif a < 0.72:
                    if idx < len(model) - 1: await pg.go_forward(); await pg.wait_for_timeout(250); idx += 1; did = 'forward'
                elif a < 0.82:
                    bl = pg.locator('.view.on .backlink')
                    if idx > 0 and await bl.count(): await bl.first.click(); await pg.wait_for_timeout(550); idx -= 1; did = 'backlink'
                elif a < 0.92:
                    # open a sheet or the menu, then swipe back: only the overlay closes
                    if r.random() < .5: await pg.evaluate("openSheet('<p>Test sheet</p>')")
                    else: await pg.evaluate('openDrawer()')
                    await pg.wait_for_timeout(150); await pg.go_back(); await pg.wait_for_timeout(300); did = 'overlay+back'
                    open_ = await pg.evaluate("document.querySelector('#sheet.on,#drawer.on')!==null")
                    if open_: print('seed', seed, 'step', step, 'overlay still open after back'); bad += 1
                    model = model[:idx + 1]   # the overlay step sits on top, so forward history is gone
                else:
                    # open a sheet and close it by tapping outside
                    await pg.evaluate("openSheet('<p>Test sheet</p>')"); await pg.wait_for_timeout(120)
                    await pg.evaluate('closeAll()'); await pg.wait_for_timeout(250); did = 'overlay+close'
                    model = model[:idx + 1]
                cur = await pg.evaluate('S.view'); hi = await pg.evaluate('S.hi'); st = await pg.evaluate('history.state')
                if cur != model[idx] or hi != idx or (st or {}).get('i') != idx or (st or {}).get('ov'):
                    print('seed', seed, 'step', step, did, 'mismatch: app', cur, hi, st, 'model', model[idx], idx); bad += 1
                    model = (await pg.evaluate('S.hist.map(e=>e&&e.v)')); idx = hi
            if errs: print('seed', seed, 'errors', errs[:2]); bad += 1
            await pg.close()
        print('problems', bad); await b.close()
asyncio.run(main())
