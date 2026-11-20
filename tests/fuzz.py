import asyncio, random, sys
from playwright.async_api import async_playwright
import os; SIM = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb_sim.js')).read()
URL = 'http://localhost:8765/'
TY = "input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=date]):not([type=time]):not([type=range]),textarea"

ACTIONS = ['title', 'copy', 'alt', 'blur', 'type', 'selectall', 'ai', 'ai_tone', 'ai_pick', 'tpl', 'photo', 'photo_none',
           'rel', 'next', 'back', 'mic', 'altai', 'cta', 'tag_rm', 'tag_add', 'pv', 'studio', 'persona', 'confirm', 'review', 'schedule', 'when_now', 'when_sched', 'arrow_next', 'create', 'close_sheet']

async def run(seed, steps=160):
    rnd = random.Random(seed); bad = []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        c = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        await c.add_init_script(SIM); pg = await c.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL + '#create'); await pg.wait_for_timeout(400)
        async def vis(sel):
            try: return await pg.locator(sel).first.is_visible()
            except Exception: return False
        async def tap(sel):
            sheet_open = await pg.evaluate("document.querySelector('#scrim').classList.contains('on')")
            if sel.startswith('#sheet') or sel.startswith('#aiopts'):
                if not await pg.evaluate("document.querySelector('#sheet').classList.contains('on')"): return False
            elif sheet_open: return False
            if await vis(sel): await pg.locator(sel).first.tap(timeout=2000, force=await pg.evaluate(f"document.querySelector('{sel}')?.getAttribute('aria-disabled')==='true'")); return True
            return False
        for i in range(steps):
            a = rnd.choice(ACTIONS); did = False
            try:
                if a in ('title', 'copy', 'alt'): did = await tap({'title': '#post-title', 'copy': '#copy', 'alt': '#alt'}[a])
                elif a == 'blur': await pg.evaluate('document.activeElement&&document.activeElement.blur()'); did = True
                elif a == 'type':
                    if await pg.evaluate(f"!!(document.activeElement&&document.activeElement.matches('{TY}'))"): await pg.keyboard.type(rnd.choice(['hi ', 'CUNY ', '! '])); did = True
                elif a == 'selectall':
                    if await pg.evaluate(f"!!(document.activeElement&&document.activeElement.matches('{TY}'))"):
                        await pg.evaluate("document.activeElement.select()"); await pg.keyboard.press('Backspace'); did = True
                elif a == 'ai': did = await tap('#btn-ai')
                elif a == 'ai_tone': did = await tap(f'#sheet [data-tone="{rnd.choice(["short","formal","emoji"])}"]')
                elif a == 'ai_pick': did = await tap(f'#aiopts .aiopt:nth-child({rnd.randint(1,3)})')
                elif a == 'tpl':
                    if await tap('#btn-flyer'):
                        await pg.wait_for_timeout(300); await tap(f'#sheet [data-lay="{rnd.choice(["Workshop","Panel","Showcase"])}"]')
                        await tap(f'#sheet [data-tpl="{rnd.choice(["none","blue","taxi","frame"])}"]'); did = await tap('#fly-apply')
                elif a == 'photo':
                    if await tap('#btn-photo'): await pg.wait_for_timeout(300); did = await tap(f'#sheet [data-ph="{rnd.randint(0,2)}"]')
                elif a == 'photo_none':
                    if await tap('#btn-photo'): await pg.wait_for_timeout(300); did = await tap('#ph-none')
                elif a == 'rel':
                    if await vis('#rel-event'): await pg.select_option('#rel-event', rnd.choice(['', 'e1', 'e2', 'e3', 'e4'])); did = True
                elif a == 'next': did = await tap('#btn-next')
                elif a == 'back': did = await tap('.view.on [data-back]')
                elif a == 'mic': did = await tap('#btn-mic'); await pg.wait_for_timeout(rnd.choice([100, 1600]))
                elif a == 'altai': did = await tap('#btn-altai')
                elif a == 'cta': did = await tap(f'#cta-row [data-cta]:nth-child({rnd.randint(1,3)})')
                elif a == 'tag_rm': did = await tap('#tag-row .tagx')
                elif a == 'tag_add':
                    if await tap('#tag-add'):
                        await pg.wait_for_timeout(300); await pg.locator('#tag-in').fill(rnd.choice(['student life', '#ai', 'cuny sps']))
                        did = await tap('#tag-save')
                elif a == 'pv': did = await tap(f'#pv [data-pv="{rnd.choice(["1","-1"])}"]')
                elif a == 'studio':
                    await pg.evaluate("closeAll();go('overview')"); await pg.wait_for_timeout(300)
                    if await tap('#v-overview .welcome [data-go="create"]'): await pg.wait_for_timeout(400); did = await tap('#studio-go')
                elif a == 'persona': await pg.evaluate("S.persona=S.persona==='contrib'?'lead':'contrib';if(S.view==='schedule')updSched()"); did = True
                elif a == 'confirm': did = (await tap('#pn-go')) or (await tap('#rv-send'))
                elif a == 'review': did = await tap('#chk-review')
                elif a == 'schedule': did = await tap('#btn-schedule')
                elif a == 'when_now': did = await tap('#v-schedule [data-when="now"]')
                elif a == 'when_sched': did = await tap('#v-schedule [data-when="schedule"]')
                elif a == 'arrow_next':
                    if await pg.evaluate(f"!!(document.activeElement&&document.activeElement.matches('{TY}'))"):
                        await pg.evaluate(f"(()=>{{const f=[...document.querySelectorAll('.view.on input,.view.on textarea')].filter(e=>e.offsetParent&&e.matches('{TY}'));const i=f.indexOf(document.activeElement);f[(i+1)%f.length].focus()}})()"); did = True
                elif a == 'create': await pg.evaluate("go('create')"); did = True
                elif a == 'close_sheet':
                    if await vis('#scrim.on'): await pg.evaluate("closeAll()"); did = True
            except Exception as e:
                if 'outside of the viewport' in str(e):
                    info = await pg.evaluate("""(()=>{const q=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return [Math.round(r.top),Math.round(r.bottom),Math.round(r.height)]};return {phone:q('#phone'),sheet:q('#sheet'),opt:q('#aiopts .aiopt'),tone:q('#sheet [data-tone]'),on:document.querySelector('#sheet').className,sheetScroll:document.querySelector('#sheet').scrollTop,sh:document.querySelector('#sheet').scrollHeight,vvh:visualViewport.height,inner:innerHeight,view:document.querySelector('.view.on').id,active:document.activeElement.id||document.activeElement.tagName}})()""")
                    bad.append(f'OUTSIDE step {i} {a}: {info}')
                bad.append(f'step {i} {a}: ' + str(e)[-700:] + ' || ' + ' | '.join(l.strip() for l in str(e).splitlines() if 'intercepts' in l or 'not stable' in l or 'outside' in l or 'not visible' in l)[:200])
            if not did: continue
            await pg.wait_for_timeout(rnd.choice([80, 250, 500]))
            await pg.wait_for_timeout(450)
            st = await pg.evaluate(f"""(()=>{{const ph=document.querySelector('#phone'),r=ph.getBoundingClientRect(),vv=visualViewport,a=document.activeElement,
              typing=!!(a&&a.matches&&a.matches('{TY}')),v=document.querySelector('.view.on'),hd=v&&v.querySelector('.top');
              let fv=true;if(typing&&!a.closest('.sheet')){{const q=a.getBoundingClientRect();fv=q.top>=(hd?hd.getBoundingClientRect().bottom:r.top)-1&&q.top+Math.min(q.height,40)<=vv.offsetTop+vv.height}}
              return {{pinned:Math.round(r.top)===Math.round(vv.offsetTop)&&Math.round(r.height)===Math.round(vv.height),headTop:hd?Math.round(hd.getBoundingClientRect().top)===Math.round(r.top):true,
                typing,cls:ph.classList.contains('typing-on'),fv,view:v&&v.id,sx:document.querySelector('#screen').scrollLeft}}}})()""")
            log = await pg.evaluate('__log'); pans = [x for x in log if x['pan']]
            if pans: bad.append(f'step {i} {a}: Safari page shift {pans}'); await pg.evaluate('__log.length=0')
            if not st['pinned']: bad.append(f'step {i} {a}: app not pinned {st}')
            if not st['headTop']: bad.append(f'step {i} {a}: header moved {st}')
            if not st['fv']: bad.append(f'step {i} {a}: field hidden {st}')
            if st['cls'] != st['typing']: bad.append(f'step {i} {a}: typing state out of sync {st}')
            if st['sx']: bad.append(f'step {i} {a}: sideways scroll {st}')
            if errs: bad.append(f'step {i} {a}: page error {errs}'); errs.clear()
        await b.close()
    return bad

async def main():
    seeds = range(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
    res = await asyncio.gather(*[run(s) for s in seeds])
    total = sum(len(r) for r in res)
    for s, r in zip(seeds, res):
        print(f'seed {s}: {len(r)} problems'); [print('   ', x) for x in r[:40]]
    print('TOTAL problems', total)
asyncio.run(main())
