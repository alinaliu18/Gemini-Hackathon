// Run: node src/live/followup.test.mjs
import assert from 'node:assert/strict';
import { createDecider, exchangeText, MAX_FOLLOWUPS } from './followup.js';

const caps = [{ role: 'interviewer', text: 'Tell me about the dashboard.' }, { role: 'candidate', text: 'We built it.' }];
assert.equal(exchangeText(caps, 0), 'We built it.');

// the backend says follow up twice; the third call is capped without asking the backend
const seen = [];
const d = createDecider({ ask: async (q, a, n) => { seen.push(n); return { action: 'follow_up', missing: 'own_action', ask: 'What did you do?' }; } });
assert.equal((await d({ args: { main_question: 'Q1' } }, caps)).action, 'follow_up');
assert.equal((await d({ args: { main_question: 'Q1' } }, caps)).action, 'follow_up');
const capped = await d({ args: { main_question: 'Q1' } }, caps);
assert.equal(capped.action, 'next');
assert.deepEqual(seen, [0, 1], `backend asked with counts ${seen}`);
assert.equal(MAX_FOLLOWUPS, 2);

// after "next" the count and the exchange start over
const later = [...caps, { role: 'interviewer', text: 'Next question.' }, { role: 'candidate', text: 'I led the launch.' }];
let gotAnswer;
const d2 = createDecider({ ask: async (q, a, n) => { gotAnswer = a; return { action: 'next', missing: null, ask: '' }; } });
await d2({ args: {} }, caps);
await d2({ args: {} }, later);
assert.equal(gotAnswer, 'I led the launch.', 'second exchange should not include the first answer');

// too slow: the old rule (one follow-up, then move on) and the timeout is reported
let timeouts = 0;
const slow = createDecider({ ask: () => new Promise(() => {}), timeoutMs: 20, onTimeout: () => { timeouts += 1; } });
assert.equal((await slow({ args: {} }, caps)).action, 'follow_up');
assert.equal((await slow({ args: {} }, caps)).action, 'next');
assert.equal(timeouts, 2);

// a backend error is treated like a timeout
const broken = createDecider({ ask: async () => { throw new Error('500'); }, timeoutMs: 50 });
assert.equal((await broken({ args: {} }, caps)).action, 'follow_up');
console.log('ALL OK');
