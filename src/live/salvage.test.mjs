// Run: node src/live/salvage.test.mjs
import assert from 'node:assert';
import { canSalvage } from './salvage.js';

const turn = { role: 'interviewer', start: 1, end: 6, text: 'Tell me about a project.' };
assert.strictEqual(canSalvage({ turns: [turn], seconds: 95, bytes: 120000 }), true, 'a real exchange is kept');
assert.strictEqual(canSalvage({ turns: [], seconds: 95, bytes: 120000 }), false, 'the interviewer never asked anything');
assert.strictEqual(canSalvage({ turns: [turn], seconds: 8, bytes: 120000 }), false, 'dropped within seconds');
assert.strictEqual(canSalvage({ turns: [turn], seconds: 95, bytes: 300 }), false, 'nothing was recorded');
assert.strictEqual(canSalvage({}), false);
console.log('ALL OK');
