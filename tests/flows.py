import asyncio, sys, json
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
OUT = '/tmp/club-hub-shots'
import os; SIM = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb_sim.js')).read()
FAILS = []; PASSES = 0

def check(cond, msg):
    global PASSES
    if cond: PASSES += 1
    else: FAILS.append(msg); print('  FAIL:', msg)

async def new_page(b):
    c = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    await c.add_init_script(SIM)
    pg = await c.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and pg.errs.append('console: ' + m.text))
    await pg.goto(URL); await pg.wait_for_timeout(500)
    return pg

async def tap(pg, sel, wait=420):
    await pg.locator(sel + ' >> visible=true').first.tap(); await pg.wait_for_timeout(wait)

STATE = """(sel)=>{const ph=document.querySelector('#phone').getBoundingClientRect();const vv=visualViewport;
 const a=document.activeElement;const v=document.querySelector('.view.on');const hd=v&&v.querySelector('.top');
 const r=a&&a!==document.body?a.getBoundingClientRect():null;
 return {phoneTop:Math.round(ph.top),phoneH:Math.round(ph.height),vvTop:vv.offsetTop,vvH:Math.round(vv.height),inner:innerHeight,
  head:hd?[Math.round(hd.getBoundingClientRect().top),Math.round(hd.getBoundingClientRect().bottom)]:null,
  field:r?[Math.round(r.top),Math.round(r.bottom)]:null,active:a?(a.id||a.tagName):null,
  typing:document.querySelector('#phone').classList.contains('typing-on'),pad:document.querySelector('#phone').classList.contains('kb-pad'),
  scroll:Math.round(document.querySelector('#screen').scrollTop),view:v?v.id:null}}"""

async def state(pg): return await pg.evaluate(STATE)

async def focus_field(pg, sel, label, how='tap'):
    n0 = await pg.evaluate('__log.length')
    if how == 'tap': await pg.locator(sel).tap()
    else: await pg.evaluate(f"document.querySelector('{sel}').focus()")
    await pg.wait_for_timeout(450)
    log = await pg.evaluate('__log')
    st = await state(pg)
    entry = log[n0] if len(log) > n0 else None
    check(entry is not None, f'{label}: keyboard opened')
    if entry:
        check(entry['pan'] == 0, f'{label}: Safari would need to shift the page (pan {entry["pan"]}px, field at {entry["top"]}-{entry["bottom"]})')
    check(st['phoneTop'] == st['vvTop'] and st['phoneH'] == st['vvH'], f'{label}: app not pinned to visible area {st}')
    if st['head']: check(st['head'][0] == st['phoneTop'], f'{label}: header not at top {st}')
    f = st['field']
    if f:
        top_ok = f[0] >= (st['head'][1] if st['head'] else st['phoneTop'])
        bottom_ok = min(f[1], f[0] + 40) <= st['vvTop'] + st['vvH'] - 4
        check(top_ok and bottom_ok, f'{label}: field not visible {st}')
    return st

async def blur(pg):
    await pg.evaluate('document.activeElement&&document.activeElement.blur()'); await pg.wait_for_timeout(600)
    st = await state(pg)
    check(st['phoneH'] == st['inner'] and st['phoneTop'] == 0, f'blur: app not back to full height {st}')
    check(not st['typing'] and not st['pad'], f'blur: typing classes left on {st}')
    return st

async def to_create(pg):
    await tap(pg, 'text=Get started'); await tap(pg, 'text=Enter demo workspace'); await tap(pg, '#v-overview >> text=Create post', 600); await tap(pg, '#studio-go', 500)
    check((await state(pg))['view'] == 'v-create', 'reached Create post')

async def shot(pg, name): await pg.screenshot(path=f'{OUT}/{name}.png')

async def flow1(b):
    print('F1 type in every field, move between fields, next, back, schedule')
    pg = await new_page(b); await to_create(pg)
    await focus_field(pg, '#post-title', 'F1 title'); await pg.keyboard.press('End'); await pg.keyboard.type(' 2026')
    await shot(pg, 'f1_title')
    await focus_field(pg, '#copy', 'F1 copy (tap while keyboard open)'); await pg.keyboard.type('Hello CUNY SPS. ')
    await shot(pg, 'f1_copy')
    await focus_field(pg, '#alt', 'F1 alt (tap while keyboard open)'); await shot(pg, 'f1_alt')
    await focus_field(pg, '#copy', 'F1 copy via arrow key', how='focus')
    await focus_field(pg, '#post-title', 'F1 title via arrow key', how='focus')
    await blur(pg)
    check(await pg.input_value('#post-title') == 'Spring AI Ethics Panel 2026', 'F1 title text kept')
    await tap(pg, '#btn-next'); check((await state(pg))['view'] == 'v-schedule', 'F1 next to step 2')
    await tap(pg, '#v-schedule [data-back]'); st = await state(pg)
    check(st['view'] == 'v-create' and st['scroll'] == 0, f'F1 back to step 1 at top {st}')
    check((await pg.input_value('#copy')).startswith('Hello'), 'F1 copy kept after back')
    await focus_field(pg, '#alt', 'F1 alt after back'); await blur(pg)
    await tap(pg, '#btn-next'); await tap(pg, '#chk-review'); await tap(pg, '#btn-schedule', 700)
    check((await state(pg))['view'] == 'v-result', 'F1 scheduled')
    await shot(pg, 'f1_result')
    check(not pg.errs, f'F1 errors {pg.errs}'); await pg.context.close()

async def flow2(b):
    print('F2 AI caption helper: pick, tones, select all, keyboard open when opening helper')
    pg = await new_page(b); await to_create(pg)
    await tap(pg, '#btn-ai'); st = await state(pg)
    check(st['active'] in ('BUTTON',) or st['active'] == '', f'F2 AI sheet opened without keyboard {st}')
    await tap(pg, '#aiopts .aiopt:nth-child(2)', 800); st = await state(pg)
    check(not st['typing'] and st['active'] not in ('copy', 'alt', 'post-title'), f'F2 AI pick did not open keyboard {st}')
    v = await pg.input_value('#copy'); check(v.startswith('Spring AI Ethics Panel is coming up'), 'F2 draft filled ' + v[:40])
    r = await pg.evaluate("(()=>{const r=document.querySelector('#copy').getBoundingClientRect();return [r.top,r.bottom]})()")
    check(r[0] > 60 and r[1] < 844, f'F2 post copy in view after AI pick {r}')
    await shot(pg, 'f2_after_ai')
    # tap into the text, select all, then iOS shows a taller keyboard bar (Proofread): no scrolling must happen
    await focus_field(pg, '#copy', 'F2 tap copy after AI')
    s0 = (await state(pg))['scroll']
    await pg.evaluate("document.querySelector('#copy').select()")
    await pg.evaluate("visualViewport._h=innerHeight-__KBH-44;visualViewport.dispatchEvent(new Event('resize'))"); await pg.wait_for_timeout(400)
    st = await state(pg); check(st['scroll'] == s0, f'F2 no scroll jump during select all ({s0} -> {st["scroll"]})')
    check(st['phoneH'] == st['vvH'], 'F2 app follows taller keyboard')
    await pg.keyboard.press('Backspace'); check(await pg.input_value('#copy') == '', 'F2 select all + delete cleared copy')
    await pg.evaluate("visualViewport._h=innerHeight-__KBH;visualViewport.dispatchEvent(new Event('resize'))"); await pg.wait_for_timeout(300)
    # open AI helper while keyboard is open
    await tap(pg, '#btn-ai', 600); st = await state(pg)
    check(not st['typing'] and st['phoneH'] == st['inner'], f'F2 opening AI helper closed keyboard {st}')
    for tone in ['formal', 'short', 'emoji', 'formal', 'short', 'emoji']:
        await tap(pg, f'#sheet [data-tone="{tone}"]', 250)
    texts = await pg.eval_on_selector_all('#aiopts .aiopt', 'e=>e.map(x=>x.textContent)')
    check(len(set(texts)) == 3, 'F2 three different drafts after toggling tones')
    await tap(pg, '#sheet [data-tone="formal"]', 250)
    await tap(pg, '#aiopts .aiopt:nth-child(1)', 800)
    check('invites you' in await pg.input_value('#copy'), 'F2 formal draft filled')
    check(not (await state(pg))['typing'], 'F2 second AI pick no keyboard')
    await focus_field(pg, '#alt', 'F2 alt after AI'); await blur(pg)
    check(not pg.errs, f'F2 errors {pg.errs}'); await pg.context.close()

async def flow3(b):
    print('F3 templates, image changes, validation')
    pg = await new_page(b); await to_create(pg)
    for k in ['blue', 'taxi', 'frame', 'none', 'blue']:
        await tap(pg, '#btn-flyer'); await tap(pg, f'#sheet [data-tpl="{k}"]', 150); await tap(pg, '#fly-apply', 350)
        hid = await pg.evaluate("document.querySelector('#flyer-layer').hidden")
        check(hid == (k == 'none'), f'F3 template {k} shown correctly')
    await focus_field(pg, '#post-title', 'F3 title with template'); await pg.keyboard.press('End'); await pg.keyboard.type('!')
    t = await pg.evaluate("document.querySelector('#flyer-layer b').textContent"); check(t.endswith('!'), 'F3 flyer title updates live')
    await blur(pg)
    await tap(pg, '#btn-photo'); await tap(pg, '#ph-none', 400)
    check(await pg.evaluate("getComputedStyle(document.querySelector('#preview-empty')).display") != 'none', 'F3 image removed')
    await tap(pg, '#btn-flyer', 300); check(not await pg.evaluate("document.querySelector('#sheet').classList.contains('on')"), 'F3 templates need an image')
    # empty copy -> Next shows the field without opening the keyboard
    await tap(pg, '#btn-next', 700); st = await state(pg)
    check(st['view'] == 'v-create' and not st['typing'], f'F3 validation keeps keyboard closed {st}')
    r = await pg.evaluate("(()=>{const r=document.querySelector('#f-copy').getBoundingClientRect();return [r.top,r.bottom]})()")
    check(r[0] >= 50 and r[1] <= 844, f'F3 bad field scrolled into view {r}')
    await shot(pg, 'f3_validation')
    await tap(pg, '#btn-photo'); await tap(pg, '#sheet [data-ph="1"]', 400)
    await pg.fill('#alt', ''); await pg.fill('#copy', 'Hi');  await blur(pg)
    await tap(pg, '#btn-next', 700); check((await state(pg))['view'] == 'v-create', 'F3 alt required with image')
    await focus_field(pg, '#alt', 'F3 alt after error'); await pg.keyboard.type('Skaters')
    await blur(pg); await tap(pg, '#btn-next'); check((await state(pg))['view'] == 'v-schedule', 'F3 next after fix')
    await tap(pg, '#v-schedule [data-when="now"]'); await tap(pg, '#chk-review'); await tap(pg, '#btn-schedule', 700)
    check(await pg.evaluate("document.querySelector('#sheet').classList.contains('on')"), 'F3 Lead gets Publish now? sheet')
    await tap(pg, '#pn-go', 700)
    check('published' in (await pg.inner_text('#result-body')).lower(), 'F3 publish now')
    await tap(pg, '#another', 500); st = await state(pg)
    check(st['view'] == 'v-create' and await pg.input_value('#copy') == '', 'F3 create another resets')
    check(not pg.errs, f'F3 errors {pg.errs}'); await pg.context.close()

async def flow4(b):
    print('F4 related event, autosaved draft, event -> create post, sign-in field')
    pg = await new_page(b)
    await tap(pg, 'text=Get started')
    await focus_field(pg, '#email', 'F4 sign-in email'); await blur(pg)
    await tap(pg, 'text=Enter demo workspace'); await tap(pg, '#v-overview >> text=Create post', 600); await tap(pg, '#studio-go', 500)
    await pg.select_option('#rel-event', 'e2'); await pg.wait_for_timeout(200)
    await tap(pg, '#btn-ai'); txt = await pg.inner_text('#aiopts'); check('Wed Nov 18' in txt, 'F4 drafts use related event')
    await tap(pg, '#aiopts .aiopt:nth-child(3)', 800)
    await focus_field(pg, '#post-title', 'F4 title'); await blur(pg)
    await pg.wait_for_timeout(900)
    check(await pg.is_visible('#saved'), 'F4 header shows Saved')
    check(not await pg.is_visible('#btn-draft'), 'F4 no Save draft button')
    await tap(pg, '#v-create [data-back]', 600); st = await state(pg); check(st['view'] == 'v-overview', 'F4 back -> overview, no pop-up')
    ov = await pg.inner_text('#ov-posts'); check('Spring AI Ethics Panel' in ov and 'Draft' in ov, 'F4 autosaved draft listed')
    await tap(pg, '#v-overview >> text=View all', 500)
    await tap(pg, '[data-more]', 400); await tap(pg, '#mk-post', 600)
    st = await state(pg); check(st['view'] == 'v-create' and await pg.input_value('#post-title') != '', f'F4 event -> create post {st}')
    await focus_field(pg, '#copy', 'F4 copy from event'); await blur(pg)
    check(not pg.errs, f'F4 errors {pg.errs}'); await pg.context.close()

async def flow5(b):
    print('F5 every screen loads; every text field on every screen behaves; chat bars stay visible')
    pg = await new_page(b); await tap(pg, 'text=Get started'); await tap(pg, 'text=Enter demo workspace')
    keys = await pg.evaluate('Object.keys(D)')
    for k in keys:
        try: await pg.evaluate(f"go('{k}')")
        except Exception as e:
            print('   (skip', k, '- detail screen opened only from a list)'); pg.errs.clear(); await pg.evaluate("go('overview')"); continue
        await pg.wait_for_timeout(250)
        ids = await pg.evaluate("""[...document.querySelectorAll('.view.on input, .view.on textarea')].filter(e=>e.offsetParent&&!['checkbox','radio','file','date','time','range'].includes(e.type)).map(e=>e.id).filter(Boolean)""")
        for i in ids:
            st = await focus_field(pg, '#' + i, f'F5 {k} #{i}')
            inbar = await pg.evaluate(f"!!document.querySelector('#{i}').closest('.bottombar')")
            if inbar:
                vis = await pg.evaluate(f"(()=>{{const r=document.querySelector('#{i}').getBoundingClientRect();return r.height>0&&r.bottom<=visualViewport.offsetTop+visualViewport.height}})()")
                check(vis, f'F5 {k} chat box stays visible above keyboard')
                await pg.keyboard.type('Hello'); await shot(pg, f'f5_{k}_{i}')
            await blur(pg)
    # detail screens reached the normal way
    for lst, act, label in [('inbox', 'openMsg', 'message'), ('forums', 'openThread', 'thread')]:
        await pg.evaluate(f"go('{lst}')"); await pg.wait_for_timeout(300)
        await tap(pg, f'[data-act="{act}"]', 400)
        ids = await pg.evaluate("""[...document.querySelectorAll('.view.on input, .view.on textarea')].filter(e=>e.offsetParent&&!['checkbox','radio','file','date','time','range'].includes(e.type)).map(e=>e.id).filter(Boolean)""")
        check(len(ids) > 0, f'F5 {label} screen has a reply box')
        for i in ids:
            await focus_field(pg, '#' + i, f'F5 {label} #{i}'); await pg.keyboard.type('Thanks!'); await shot(pg, f'f5_{label}'); await blur(pg)
    # chat send works
    await pg.evaluate("go('assistant')"); await pg.wait_for_timeout(300)
    await pg.locator('#chatin').tap(); await pg.keyboard.type('Draft a post'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(900)
    n = await pg.evaluate("document.querySelectorAll('#chatlog .msg').length"); check(n >= 2, f'F5 assistant replies ({n} messages)')
    check(not pg.errs, f'F5 errors {pg.errs}'); await pg.context.close()

async def flow6(b):
    print('F6 desktop layout unchanged')
    c = await b.new_context(viewport={'width': 1280, 'height': 900})
    pg = await c.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(500)
    r = await pg.evaluate("(()=>{const r=document.querySelector('#phone').getBoundingClientRect();return [r.width,r.height,getComputedStyle(document.querySelector('#phone')).position]})()")
    check(r[0] == 390 and r[1] == 844 and r[2] == 'relative', f'F6 desktop phone frame {r}')
    await pg.screenshot(path=f'{OUT}/f6_desktop.png'); check(not errs, f'F6 errors {errs}'); await c.close()

async def flow7(b):
    print('F7 v12 Create post: where are you posting, dictate, word limit, CTA, hashtags, AI alt, flyer layouts, preview arrows')
    pg = await new_page(b)
    await tap(pg, 'text=Get started'); await tap(pg, 'text=Enter demo workspace')
    await tap(pg, '#v-overview >> text=Create post', 600)
    check(await pg.evaluate("document.querySelector('#sheet').classList.contains('on')") and 'Where are you posting' in await pg.inner_text('#sheet'), 'F7 Create post opens Where are you posting?')
    check(await pg.inner_text('#soc-n') == '2 selected', 'F7 Facebook + Instagram on by default')
    await tap(pg, '#sheet [data-soc="fb"]', 150); await tap(pg, '#sheet [data-soc="ig"]', 150)
    await tap(pg, '#studio-go', 400); check((await state(pg))['view'] == 'v-overview', 'F7 needs one social platform')
    await pg.locator('#sheet [data-later="YouTube"]').tap(force=True); await pg.wait_for_timeout(300); check('later phase' in await pg.inner_text('#toast'), 'F7 YouTube says coming later')
    await tap(pg, '#sheet [data-soc="fb"]', 150); await tap(pg, '#sheet [data-dst="blog"]', 150)
    await shot(pg, 'f7_studio')
    await tap(pg, '#studio-go', 600); check((await state(pg))['view'] == 'v-create', 'F7 studio -> step 1')
    check(not await pg.is_visible('#v-create .ctx'), 'F7 no step text in header')
    # dictate
    await tap(pg, '#btn-mic', 1700)
    check('Bring a friend' in await pg.input_value('#copy'), 'F7 dictate adds text')
    check(not (await state(pg))['typing'], 'F7 dictate does not open keyboard')
    # word counter + limit
    check(await pg.inner_text('#copy-count') == '7 / 500 words', 'F7 word counter ' + await pg.inner_text('#copy-count'))
    await pg.evaluate("copy.value='word '.repeat(501);copy.oninput()")
    check('over' in await pg.get_attribute('#copy-count', 'class'), 'F7 counter turns red over 500')
    await tap(pg, '#btn-next', 600); check((await state(pg))['view'] == 'v-create' and '500 words' in await pg.inner_text('#copy-err'), 'F7 over 500 words blocks Preview')
    await pg.evaluate("copy.value='Join the AI Club for our Spring AI Ethics Panel. Q&A after.';copy.oninput()")
    # CTA
    await tap(pg, '#cta-row [data-cta="Learn more"]', 200)
    check(await pg.evaluate("S.cta") == 'Learn more', 'F7 CTA picks one')
    await tap(pg, '#cta-other', 500)
    await focus_field(pg, '#cta-in', 'F7 CTA other field'); await pg.keyboard.type('Get tickets'); await tap(pg, '#cta-save', 500)
    check(await pg.evaluate("S.cta") == 'Get tickets' and 'Get tickets' in await pg.inner_text('#cta-row'), 'F7 custom CTA')
    # hashtags
    await tap(pg, '#tag-row [aria-label="Remove #AiEthics"]', 200)
    check(await pg.evaluate("S.tags.join(' ')") == '#CunySps #AIClub', 'F7 remove hashtag')
    await tap(pg, '#tag-add', 500); await focus_field(pg, '#tag-in', 'F7 hashtag field'); await pg.keyboard.type('student life'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400)
    check(await pg.evaluate("S.tags.includes('#StudentLife')"), 'F7 add hashtag auto-capitalized ' + str(await pg.evaluate("S.tags")))
    # AI alt
    await tap(pg, '#btn-photo'); await tap(pg, '#sheet [data-ph="0"]', 400); await pg.fill('#alt', ''); await blur(pg)
    await tap(pg, '#btn-altai', 300); check(await pg.input_value('#alt') != '', 'F7 AI Suggest fills alt text')
    check(not (await state(pg))['typing'], 'F7 AI Suggest does not open keyboard')
    # flyer layouts
    await tap(pg, '#btn-flyer', 500); await tap(pg, '#sheet [data-lay="Panel"]', 150)
    await focus_field(pg, '#fly-det', 'F7 flyer details field'); await pg.keyboard.type('Room 402')
    check('Room 402' in await pg.inner_text('#tpls'), 'F7 details show on templates live')
    await pg.evaluate('document.activeElement.blur()'); await pg.wait_for_timeout(400)
    await tap(pg, '#sheet [data-tpl="taxi"]', 150); await shot(pg, 'f7_flyer'); await tap(pg, '#fly-apply', 500)
    fl = await pg.inner_text('#flyer-layer'); check('Room 402' in fl and 'PANEL' in fl.upper(), 'F7 flyer shows layout + details')
    await pg.wait_for_timeout(800); check(await pg.is_visible('#saved'), 'F7 autosaved')
    # preview
    await tap(pg, '#btn-next', 600); check((await state(pg))['view'] == 'v-schedule', 'F7 Preview step')
    check(await pg.inner_text('#v-schedule .title') == 'Preview', 'F7 header says Preview')
    check(await pg.locator('#v-schedule [data-acct]').count() == 0, 'F7 no Post to switches')
    check('simulation' not in (await pg.inner_text('#v-schedule')).lower(), 'F7 no simulation labels')
    pv = await pg.inner_text('#pv'); check('Facebook' in pv and '1 of 1' in pv and 'Get tickets' in pv and '#StudentLife' in pv, 'F7 Facebook preview uses the post ' + pv[-80:])
    check(await pg.get_attribute('#pv [data-pv="1"]', 'aria-disabled') == 'true', 'F7 one platform: arrows off')
    await shot(pg, 'f7_preview')
    await tap(pg, '#chk-review'); await tap(pg, '#btn-schedule', 700)
    res = await pg.inner_text('#result-body'); check('AI Club Blog' in res and 'Instagram' not in res, 'F7 result lists Facebook + Blog only')
    check(not pg.errs, f'F7 errors {pg.errs}'); await pg.context.close()

async def flow8(b):
    print('F8 roles: Contributor submits for review, Lead sees it, approves / asks for changes; preview arrows with 2 platforms')
    pg = await new_page(b)
    await tap(pg, 'text=Get started'); await tap(pg, '[data-persona="contrib"]', 600)
    check('Sofia' in await pg.inner_text('#greet') and 'Contributor' in await pg.inner_text('#ov-role'), 'F8 Contributor overview')
    check(await pg.inner_text('#ov-review') == '', 'F8 Contributor has no review queue')
    await tap(pg, '#v-overview >> text=Create post', 600); await tap(pg, '#studio-go', 600)
    await pg.fill('#copy', 'Office hours recap. Thanks for coming!'); await blur(pg)
    await tap(pg, '#btn-next', 600)
    check(await pg.inner_text('#pv .pvnav span') == 'Facebook · 1 of 2', 'F8 preview label')
    await tap(pg, '#pv [data-pv="1"]', 300); check('Instagram' in await pg.inner_text('#pv .pvnav'), 'F8 arrow to Instagram')
    await tap(pg, '#pv [data-pv="-1"]', 300); check('Facebook' in await pg.inner_text('#pv .pvnav'), 'F8 arrow back to Facebook')
    check('Submit' in await pg.inner_text('#btn-schedule'), 'F8 Contributor button says Submit')
    await tap(pg, '#chk-review'); await tap(pg, '#btn-schedule', 700)
    sh = await pg.inner_text('#sheet'); check('Submit for review?' in sh and 'A Club Lead will review' in sh, 'F8 submit sheet')
    await focus_field(pg, '#rv-note', 'F8 reviewer note field'); await pg.keyboard.type('Please check the room')
    await shot(pg, 'f8_submit')
    await pg.evaluate('document.activeElement.blur()'); await pg.wait_for_timeout(400)
    await tap(pg, '#rv-send', 800)
    check('Sent for review' in await pg.inner_text('#result-body'), 'F8 sent for review screen')
    await tap(pg, '#v-result [data-go="overview"]', 600)
    check('In review' in await pg.inner_text('#ov-posts'), 'F8 Contributor sees In review')
    # Lead
    await pg.evaluate("go('signin')"); await pg.wait_for_timeout(400); await tap(pg, '[data-persona="lead"]', 600)
    q = await pg.inner_text('#ov-review'); check('Waiting for your review' in q and 'Please check the room' in q, 'F8 Lead sees the submission')
    check(await pg.locator('[data-rv-ok]').count() == 2, 'F8 two items waiting')
    await tap(pg, '[data-rv-ok]', 500)
    check('scheduled' in (await pg.inner_text('#toast')).lower() and await pg.locator('[data-rv-ok]').count() == 1, 'F8 approve')
    await tap(pg, '[data-rv-chg]', 600); await tap(pg, '#chg-send', 300)
    check(await pg.evaluate("document.querySelector('#sheet').classList.contains('on')"), 'F8 ask for changes needs a note')
    await focus_field(pg, '#chg-note', 'F8 changes note field'); await pg.keyboard.type('Use the new room')
    await pg.evaluate('document.activeElement.blur()'); await pg.wait_for_timeout(400); await tap(pg, '#chg-send', 600)
    check(await pg.inner_text('#ov-review') == '' and 'Changes asked' in await pg.inner_text('#ov-posts'), 'F8 sent back, queue empty')
    # Lead schedule goes straight out, no sheet
    await tap(pg, '#v-overview >> text=Create post', 600); await tap(pg, '#studio-go', 600)
    await pg.fill('#copy', 'Hello'); await blur(pg); await tap(pg, '#btn-next', 600)
    check(await pg.inner_text('#btn-schedule') == 'Schedule post', 'F8 Lead button says Schedule post')
    await tap(pg, '#chk-review'); await tap(pg, '#btn-schedule', 700)
    check((await state(pg))['view'] == 'v-result', 'F8 Lead schedule without extra sheet')
    check(not pg.errs, f'F8 errors {pg.errs}'); await pg.context.close()

async def main():
    import os; os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        for f in [flow1, flow2, flow3, flow4, flow5, flow6, flow7, flow8]:
            try: await f(b)
            except Exception as e: FAILS.append(f'{f.__name__} crashed: {e}'); print('  CRASH', f.__name__, str(e)[:300])
        await b.close()
    print(f'\n{PASSES} checks passed, {len(FAILS)} failed')
    for x in FAILS: print(' -', x)
asyncio.run(main())
