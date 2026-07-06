import type { ChatAnswer } from "./chat-types";

// Deterministic compliance net (independent of the model): catches buy/sell/advice
// asks. Deliberately does NOT match neutral "what should I watch" questions.
const ADVICE =
  /\b(is\s+(this|it|that|now)\s+a\s+(good\s+)?(buy|sell)|(should|shall)\s+(i|we)\s+(buy|sell|invest|book|exit|enter|hold)|buy\s+(it|this|now)|sell\s+(it|this|now)|(price\s+)?target|multibagger|multi-bagger|sure[-\s]?shot|guaranteed\s+returns?|stock\s+tip|give\s+me\s+a\s+tip|when\s+(should|to)\s+(i\s+)?(buy|sell)|entry\s+price|stop[-\s]?loss|book\s+profit|will\s+(it|this)\s+(double|moon|crash))\b/i;

export function isAdviceRequest(q: string): boolean {
  return ADVICE.test(q || "");
}

// Output-side net: detects advice ASSERTIONS in text Maven is about to present as its own
// (vs. ADVICE above, which detects advice REQUESTS in user queries). Used to fail-closed when
// client-supplied conversation context tries to smuggle a buy/sell call through a
// transformation ("summarize in bullets" over an injected fake previous answer).
const ADVICE_ASSERTION =
  /\b(strong (buy|sell)|buy now|sell now|must[- ]?buy|(is|are|remains?) a (strong )?(buy|sell|hold)\b|rating[:\s]+(buy|sell|accumulate)|(price )?target( price)? of|target price|price target|upside of \d|\d+%\s*upside|multibagger|multi-bagger|sure[-\s]?shot|guaranteed returns?|book profits?|stop[-\s]?loss at|entry (point|price)|(accumulate|add) on dips|double your money)\b/i;

export function containsAdviceAssertion(text: string): boolean {
  return ADVICE_ASSERTION.test(text || "");
}

export function refusalAnswer(_q: string): ChatAnswer {
  return {
    headline: "I can explain the setup, but I cannot tell you to buy or sell",
    summary:
      "Maven is an educational research tool, not an adviser. I will not give buy/sell/hold calls, price targets, or tips. I can explain what is driving a name or sector and what to watch, so you can decide for yourself.",
    blocks: [
      { type: "point", title: "What I can do", body: "Explain the mechanism - why a stock or sector is moving, the macro and flows behind it, and the risks on both sides." },
      { type: "risk", title: "Why no call", body: "A recommendation depends on your goals, risk tolerance and horizon, which I do not know. Acting on a generic call can be harmful." },
      { type: "takeaway", title: "India takeaway", body: "Ask 'why is X moving' or 'what should I watch on X' and I will give the drivers and risks. Educational only, not investment advice." },
    ],
    citations: [{ label: "Maven policy", time: "" }],
    followups: ["Why is this moving?", "What are the risks here?", "Explain the macro backdrop"],
    demo: false,
  };
}