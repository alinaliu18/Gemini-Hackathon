// Browser side of decide_next_step: keeps count of follow-ups on the current main question, sends the candidate's words
// to the backend, and never leaves the interviewer waiting. The count is kept here, not taken from the interviewer,
// because the model's own count can drift; the backend caps it again (pipeline/followup.py).

export const MAX_FOLLOWUPS = 2;
export const BROWSER_TIMEOUT_MS = 3000; // the backend gives up at 2 s; this covers the round trip on a slow connection

// What the candidate said since caption `from`: the whole exchange on the current main question.
export function exchangeText(captions, from) {
  return captions.slice(from).filter((c) => c.role === 'candidate').map((c) => c.text.trim()).join(' ').trim();
}

// The old rule, used when no decision arrives in time: one follow-up per main question.
export const fallback = (asked) => (asked >= 1 ? { action: 'next', missing: null, ask: '' } : { action: 'follow_up', missing: null, ask: '' });

/**
 * ask(main_question, answer, followups_asked) -> Promise of {action, missing, ask} from the backend.
 * Returns handle({name, args}, captions) -> Promise of the tool result for the interviewer.
 */
export function createDecider({ ask, timeoutMs = BROWSER_TIMEOUT_MS, onTimeout = () => {}, onDecision = () => {} }) {
  let asked = 0;
  let from = 0;
  return async function handle({ args }, captions) {
    const answer = exchangeText(captions, from) || String(args.answer || '');
    let decision;
    if (asked >= MAX_FOLLOWUPS) decision = { action: 'next', missing: null, ask: '', source: 'cap' };
    else {
      let timer;
      const late = new Promise((resolve) => { timer = setTimeout(() => resolve(null), timeoutMs); });
      try { decision = await Promise.race([ask(String(args.main_question || ''), answer, asked), late]); }
      catch { decision = null; }
      clearTimeout(timer);
      if (!decision || !['follow_up', 'next'].includes(decision.action)) {
        decision = { ...fallback(asked), source: 'browser_timeout' };
        onTimeout(asked);
      }
    }
    if (decision.action === 'follow_up') asked += 1;
    else { asked = 0; from = captions.length; } // the next main question's exchange starts after this point
    onDecision(decision);
    return { action: decision.action, missing: decision.missing || '', ask: decision.ask || '' };
  };
}
