// Run: node src/jobWords.test.mjs
// The same cases the backend test reads, so the form and the server agree on what counts as a word.
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { countWords, jobTooShort, MIN_JD_WORDS } from './jobWords.js';

const cases = JSON.parse(readFileSync(new URL('../tests/fixtures/word_count_cases.json', import.meta.url), 'utf8'));
for (const c of cases) assert.strictEqual(countWords(c.text), c.words, JSON.stringify(c));

assert.strictEqual(MIN_JD_WORDS, 20);
assert.strictEqual(jobTooShort('one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty'), '');
assert.match(jobTooShort('Product manager intern'), /only 3 words.*at least 20 words/);
assert.match(jobTooShort('Intern'), /only 1 word\./);
console.log('ALL OK');
