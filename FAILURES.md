# Failure analysis (threshold 0.30, all 40 questions)

Seven of the 35 answerable questions fail (1 wrong answer, 6 mistaken refusals), plus two weaknesses in the conflict handling. Grouped by cause.

## 1. Vocabulary gap: the question does not use the article's words (refused)
| Q | Question | Assistant | Why |
|---|---|---|---|
| Q05 | "package stuck on the same status for a week" | refused (coverage 0.12); KB-09 not in top 5 | "week" vs "7 days", "stuck" vs "has not moved" |
| Q15 | "send back something I bought by mistake" | refused (0.15); KB-12 not in top 5 | "send back" vs "return" |
| Q27 | "can't remember how to get into my profile" | refused (0.20); KB-20 not in top 5 | "profile" vs "account", "get into" vs "login" |
| Q22 | "broken item. How fast must I report it?" | refused (0.25); KB-16 is ranked first | "fast" is not in the article, which says "within 48 hours" |

Safe failures (a refusal, not a wrong answer) but real misses. A lexical method cannot fix them; embeddings or query rewriting could. I did not add synonyms, because that would be tuning on the evaluation questions.

## 2. A word that needs world knowledge
**Q17 "Can you deliver to Switzerland?"** Refused (0.19). KB-11 says "we do not ship outside the EU", but the assistant would need to know that Switzerland is not in the EU. The unseen word lowers coverage, the same mechanism that correctly refuses Q06 (Lyon): it cannot tell "unknown subject" from "known subject, unknown country".

## 3. The wrong article is ranked first
- **Q08 "How long do refunds take?"** BM25 ranks KB-09 (lost parcel, "refund you") above KB-15 (refunds). The answer is the investigation sentence, with full coverage (1.0): **a confident wrong answer**, the only one left. The right articles (KB-15, KB-13) are below it. The conflict detector stays silent because the top sentence matches only one of the two question words.
- **Q10 "How fast is Express delivery and what is the order cut-off time?"** The stale KB-07 (2022) outranks KB-06 (2026) and covers only 0.23 of the question, so the assistant refuses. Dates play no part in ranking any more, so nothing corrects a stale article that scores clearly higher.

## 4. Conflict handling: what works and what does not
- **Works:** Q04 now shows the general 30 days (KB-12) and then the sale's 14 days (KB-13); Q03 shows 9.90 EUR (KB-07, 2022) and 7.90 EUR (KB-06, 2026) with both dates. On the 40 questions only these two answers carry a conflict note and both are real contradictions.
- **Fixed: the stale article no longer leads (Q03):** conflicting answers are now listed newest first (7.90 EUR from 2026, then 9.90 EUR from 2022). For Q04 this puts the sale exception (14 days) first; the text says the articles differ and shows both dates, but a careless reader of Q04 may take the exception as the general rule. Newest-first is an ordering, not a verdict.
- **Only figures are compared.** Two articles that disagree in words (no number, or numbers with different units such as "5 business days" vs "30 days") are not detected. Other known contradictions in the KB (cut-off 12:00 vs 14:00, 48 hours vs next working day) are only caught when the sentence chosen for the question contains the figures.
- **Narrow by design and tuned on the 40:** the guards (same category, top sentence matches every question word, 80% score ratio) were added after seeing false notes, so recall of real conflicts on new questions is unknown.

## 5. Fixed since the first version: Q07
"How long is a gift card valid?" used to return the amounts and cash sentences (words "gift" and "card" in every sentence outweighed "valid"). Weighting words by rarity inside the article fixes it (answer now contains "valid for 24 months"). One other idea, re-ranking the top 5 articles by best sentence, made results worse (27 to 24 correct) and was dropped.

## 6. Unanswerable questions: right result, thin margin
All 5 are refused (coverage 0.00 to 0.28), but Q30 (0.278) and Q38 (0.268) sit just under the threshold, and refused answerable Q22 (0.25) and Q10 (0.23) sit at the same level. The threshold cannot separate them, and five questions are too few to say it generalises.

## Data issues noticed (not edited)
- KB-06 and KB-07 contradict each other on price, speed, cut-off and free-delivery threshold. KB-13 differs from KB-12/KB-15 on return and refund delays (sale exception).
- Q04 and Q08 require both numbers in the answer; a single-source answer can never pass.
- Q17's keyword is a whole sentence from KB-11; Q02's keys accept an answer that omits Visa and Mastercard.
