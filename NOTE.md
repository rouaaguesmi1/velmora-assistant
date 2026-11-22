# Design note: Velmora help-center assistant

## 1. Need and assumptions
The team will only trust an assistant it can measure, so the evaluation matters more than the answers. Assumptions: a confident wrong answer is worse than a refusal (the threshold score counts it as −2 against +1 for a correct answer), but an assistant that refuses everything is useless; "correct" means the reader gets the useful, correct fact; nothing outside the 30 articles may be used.

## 2. Architecture, and two hesitations
BM25 retrieval over the articles. If the top article covers too little of the question, the assistant says "I don't know" with no citation. Otherwise it copies the 2 best sentences, citing the article id and date. If another article of the same category gives a different figure for the same unit, both answers are shown, newest first, with dates. Python standard library only, no randomness.
- *Abstention signal:* raw BM25 scores depend on question length, so I use the share of the question's idf weight found in the top article.
- *Contradictions:* I hesitated between newest-wins (simple, but wrong for exceptions such as the sale terms in Q04), refusing (useless for Express questions) and showing both. I chose showing both; the cost is detection code that only compares figures.

## 3. Tested and not tested
**Tested:** 22 unit tests cover recall@k on a hand-made example, refusal counting, the keyword judge, judge-vs-review agreement, threshold choice, figure comparison, parsing, and behaviour on the real KB. On the 40 questions: recall@1/3/5 = 80.0 / 88.6 / 91.4%; 28/35 correct; 1 confident wrong answer; 6 mistaken refusals; 5/5 unanswerable refused. Two runs give identical files.

**Not tested, so do not trust these numbers too much:**
- *Generalisation:* all 40 questions guided my choices (threshold, 2 sentences, conflict guards). There is no held-out set, so the results are optimistic. Cross-validation (27/35) only covers the threshold.
- *Refusals:* 5 unanswerable questions are too few. Their coverage (0.00–0.28) overlaps that of the 6 answerable questions refused by mistake (0.12–0.25), so no threshold separates them.
- *Real customers:* no typos, no French, no multi-part questions beyond the 40 given.

## 4. Cut
Embeddings or a second retriever, conflicts that do not involve numbers, and an LLM. A re-ranking idea lowered results (27 → 24 correct) and was dropped. I did more optional items than the one or two suggested (threshold table, contradiction handling, judge-check tool, cross-validation); the README explains each and any can be removed.

## 5. AI use

I used AI throughout development as a coding assistant to help implement parts of the project, explore solutions, write tests, and improve documentation. I guided the development, made the architectural and technical decisions, and reviewed the generated code rather than accepting suggestions blindly.
I validated the final result by running all tests, comparing two evaluation runs for identical outputs, checking the original files for unintended changes, and reviewing each failure against the knowledge base.

## 6. One more day
1. **A blind red-team set.** A colleague writes 40 new questions designed to break the assistant: typos, French, two topics in one question, "do you ship to Jersey?", and many more unanswerable ones. I run the harness once, report the numbers untuned, and only then fix things.
2. **A real human review of the judge** by two people, with their agreement measured.
3. **Fix the vocabulary-gap refusals** (Q05, Q15, Q27) by comparing embeddings with BM25 on recall only, leaving the abstention rule untouched.
4. **Treat the root causes:** ask the help-center owners to fix KB-07 and flag the sale article as an exception, so the assistant does not have to hide a data problem.
5. **A "hand over" mode:** when it refuses, offer the support contact and log the question, so refusals become a source of new unanswerable examples.

## Limits
**Invented answers.** It only copies sentences, so it cannot invent text, but it can copy the wrong ones with full confidence (Q08, from the wrong article). Next: show the source article beside the answer; sample answers weekly.
**Old or contradicting articles.** Rule: if a same-category article gives a different figure for the same unit, show both with dates. It works for Q03 and Q04, but it is blind to contradictions without figures, may put an exception first (Q04), and its guards were tuned on the 40. Next: ask the owners to fix KB-07; mark the sale article as an exception.
**No answer in the help center.** It refuses with no citation when the question's words are unfamiliar (5/5 here), but the same signal wrongly refuses 6 answerable questions with unusual wording, and 5 questions are too few to trust the threshold. Next: many more unanswerable examples, a check that the sentence really answers the question, embeddings for the vocabulary gap.


