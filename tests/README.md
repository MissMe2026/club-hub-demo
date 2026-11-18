# Demo tests (not part of the app)

Run before every push. They need Python Playwright and Chrome.

```
python3 -m http.server 8765            # from the repo root
python3 tests/flows.py                 # every posting path + every text field, with a simulated iPhone keyboard
python3 tests/fuzz.py 10               # 10 random-order sessions through Create post
```

`kb_sim.js` is a test-only stand-in for the iPhone keyboard. It shrinks the visible area like Safari and reports a
"page shift" whenever Safari would have to move the page to reveal a field (the v7 glitch). Both scripts should end with 0 failures.
