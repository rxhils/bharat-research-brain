// Canonicalizes a COPY of the user's query for regex intent classification/routing ONLY.
// Never shown to the user, never sent to an LLM - callers keep the original verbatim.
// Pure and deterministic: no Date, no randomness, no I/O. Feeds answerTypeRouter-style regexes.

const APOS = "['’]"; // straight ' or curly ' - weekday/today possessives use either

// Ordered single-word / possessive rules applied AFTER multi-word phrases.
// Each pattern is word-boundary anchored so we never corrupt substrings ("supermarket" stays intact).
const WORD_RULES: Array<[RegExp, string]> = [
  // British -> US spelling
  [/\banalyse\b/g, "analyze"],
  [/\bsummarise\b/g, "summarize"],
  // synonyms that mean "give me a summary"
  [/\brecap\b/g, "summarize"],
  // weekday plural/possessive -> singular (all 7 days)
  [new RegExp(`\\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:s|${APOS}s)\\b`, "g"), "$1"],
  // today/yesterday possessive+plural -> singular
  [new RegExp(`\\btoday(?:s|${APOS}s)\\b`, "g"), "today"],
  [new RegExp(`\\byesterday(?:s|${APOS}s)\\b`, "g"), "yesterday"],
  // plural -> singular; only "markets", never touch an already-singular "market"
  [/\bmarkets\b/g, "market"],
  // standalone "wrap" -> "summary" (the "market wrap" phrase is handled earlier)
  [/\bwrap\b/g, "summary"],
  // domain synonyms
  [/\bsession\b/g, "market day"],
  [/\bbourses\b/g, "market"],
];

export function normalizeForClassification(query: string): string {
  let s = (query || "").toLowerCase();

  // Multi-word phrases FIRST so single-word rules below don't split them apart.
  s = s.replace(/\bdalal street\b/g, "indian market");
  s = s.replace(/\bmarket wrap\b/g, "market summary");
  s = s.replace(/\bwhat happened\b/g, "summarize");

  // Stock-mover phrasings -> canonical gainer/loser/most-active tokens so the leaderboard router
  // (answerTypeRouter MOVERS / intentClassifier top_stock_movers) fires on natural language.
  s = s.replace(/\b(increased|went up|gone up|rose|risen|gained|rising|climbed|advanced|surged|jumped|rallied)(\s+the)?\s+most\b/g, "gainers");
  s = s.replace(/\b(fell|fallen|decreased|went down|gone down|dropped|declined|lost|losing|slid|sank|crashed|tanked|plunged)(\s+the)?\s+most\b/g, "losers");
  s = s.replace(/\bup the most\b/g, "gainers");
  s = s.replace(/\bdown the most\b/g, "losers");
  s = s.replace(/\b(most active|highest volume|most traded|highest traded value|most heavily traded)\b/g, "most active");
  s = s.replace(/\bindividual (stocks?|equit\w+|companies|shares?)\b/g, "stocks");
  s = s.replace(/\blisted companies\b/g, "stocks");
  s = s.replace(/\bshares\b/g, "stocks");

  for (const [re, repl] of WORD_RULES) s = s.replace(re, repl);

  // Collapse any whitespace introduced/left over into single spaces, trim ends.
  return s.replace(/\s+/g, " ").trim();
}
