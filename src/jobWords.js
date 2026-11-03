// How long a job description must be, counted the way the backend counts it (pipeline/inputs.py). Both read
// tests/fixtures/word_count_cases.json, so a description that passes here cannot be refused by the server.
export const MIN_JD_WORDS = 20;

const LATIN = /[A-Za-z0-9À-ɏ]+(?:['’.\-][A-Za-z0-9À-ɏ]+)*/g;
const CJK = /[぀-ヿ㐀-䶿一-鿿가-힯]/g; // no spaces in these languages: two characters count as one word

export function countWords(text = '') {
  return (text.match(LATIN) || []).length + Math.floor(((text.match(CJK) || []).length + 1) / 2);
}

// The line to show when the description is too short to aim questions at, or '' when it is long enough.
export function jobTooShort(text = '') {
  const n = countWords(text);
  if (n >= MIN_JD_WORDS) return '';
  return `The job description is only ${n} word${n === 1 ? '' : 's'}. The interviewer aims its questions at it, so a short one gives generic questions. Paste the responsibilities and requirements, at least ${MIN_JD_WORDS} words.`;
}
