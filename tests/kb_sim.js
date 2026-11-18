// Test-only stand-in for the iPhone keyboard (never shipped). It shrinks the visual viewport like iOS
// and records a "pan" whenever Safari would have to shift the page to reveal the focused field.
(() => {
  const f = new EventTarget();
  f.offsetTop = 0; f.offsetLeft = 0; f.scale = 1; f._open = false; f._h = undefined;
  Object.defineProperty(f, 'height', { get() { return f._h ?? innerHeight; } });
  Object.defineProperty(f, 'width', { get() { return innerWidth; } });
  Object.defineProperty(window, 'visualViewport', { configurable: true, get() { return f; } });
  const KBH = 347;
  window.__KBH = KBH;
  window.__log = [];
  const TY = 'input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=date]):not([type=time]):not([type=range]),textarea';
  const fire = () => { f.dispatchEvent(new Event('resize')); f.dispatchEvent(new Event('scroll')); };
  document.addEventListener('focusin', e => {
    const el = e.target; if (!el.matches || !el.matches(TY)) return;
    setTimeout(() => {
      const r = el.getBoundingClientRect();
      const visBottom = f._open ? f.offsetTop + f._h : innerHeight - KBH;
      const need = r.top + Math.min(r.height, 40);
      let pan = 0;
      if (need > visBottom - 4) pan = Math.round(need - visBottom + 20);
      window.__log.push({ id: el.id || el.className, pan, top: Math.round(r.top), bottom: Math.round(r.bottom) });
      f._open = true; f._h = innerHeight - KBH; f.offsetTop = (f.offsetTop || 0) + pan; fire();
    }, 0);
  }, true);
  document.addEventListener('focusout', () => {
    setTimeout(() => {
      const a = document.activeElement; if (a && a.matches && a.matches(TY)) return;
      f._open = false; f._h = undefined; f.offsetTop = 0; fire();
    }, 30);
  }, true);
})();
