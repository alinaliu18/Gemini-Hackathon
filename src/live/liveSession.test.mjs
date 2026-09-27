// Run: node src/live/liveSession.test.mjs
import assert from 'node:assert';
import { toBase64, pcm16ToFloat } from './liveSession.js';

const pcm = new Int16Array([0, 16384, -16384, 32767, -32768]);
const back = pcm16ToFloat(toBase64(pcm.buffer));  // what we send up == what we decode down (same 16-bit LE format)
assert.deepStrictEqual([...back].map((x) => +x.toFixed(4)), [0, 0.5, -0.5, 1, -1]);
assert.strictEqual(pcm16ToFloat(toBase64(new Int16Array(40000).buffer)).length, 40000); // large chunk, no stack overflow
console.log('ALL OK');
