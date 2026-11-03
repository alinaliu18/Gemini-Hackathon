// When the connection to the live interviewer drops, the recording made so far is still on this device. It is worth
// turning into a report only if it holds a real exchange: the interviewer asked something and the candidate spoke for a
// while. Shorter than that, a report would only say "no answers found", so the person is better off starting again.
export const MIN_SALVAGE_SECONDS = 20;
export const MIN_SALVAGE_BYTES = 8000; // an empty webm container is a few hundred bytes; a few seconds of speech is more than this

export function canSalvage({ turns = [], seconds = 0, bytes = 0 }) {
  return turns.length >= 1 && seconds >= MIN_SALVAGE_SECONDS && bytes >= MIN_SALVAGE_BYTES;
}
