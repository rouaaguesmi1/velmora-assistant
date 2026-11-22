"""Pure evaluation functions, so they are easy to unit-test."""


def recall_at_k(ranked_ids, relevant_ids, k):
    """1.0 if at least one relevant article is among the first k ranked ids, else 0.0."""
    if not relevant_ids:
        raise ValueError("recall is undefined without relevant articles")
    return float(any(r in set(ranked_ids[:k]) for r in relevant_ids))


def keywords_match(answer_text, keywords):
    """The keyword judge: every keyword must appear in the answer (ignoring case and spacing)."""
    if not keywords:
        return False
    norm = lambda t: " ".join(t.lower().replace("\u00a0", " ").split())
    return all(norm(k) in norm(answer_text) for k in keywords)


def summarise(rows, threshold=None):
    """rows: one dict per question with answerable, ranking, sources, coverage, abstained, keywords_ok.
    With `threshold`, the abstention decision is recomputed from `coverage` (used for the threshold table)."""
    def refused(r):
        return r["coverage"] < threshold if threshold is not None else r["abstained"]

    ans = [r for r in rows if r["answerable"]]
    un = [r for r in rows if not r["answerable"]]
    s = {"n_answerable": len(ans), "n_unanswerable": len(un)}
    for k in (1, 3, 5):
        s[f"recall@{k}"] = sum(recall_at_k(r["ranking"], r["sources"], k) for r in ans) / len(ans) if ans else None
    s["correct"] = sum(1 for r in ans if not refused(r) and r["keywords_ok"])
    s["wrong_confident"] = sum(1 for r in ans if not refused(r) and not r["keywords_ok"])
    s["refused_by_mistake"] = sum(1 for r in ans if refused(r))
    s["unanswerable_refused"] = sum(1 for r in un if refused(r))
    return s


def judge_agreement(rows, human):
    """Compare the keyword judge with a manual review.
    rows: result rows (id, keywords_ok).  human: {id: True/False}, the reviewer's 'is this answer correct?'.
    Only reviewed rows count."""
    pairs = [(bool(r["keywords_ok"]), human[r["id"]]) for r in rows if r["id"] in human]
    return {
        "reviewed": len(pairs),
        "agree": sum(j == h for j, h in pairs),
        "judge_too_generous": sum(j and not h for j, h in pairs),   # judge says correct, reviewer says not
        "judge_too_strict": sum(h and not j for j, h in pairs),
        "correct_after_review": sum(h for _, h in pairs),
    }


def utility(s):
    """One number to compare thresholds: +1 per correct answer, -2 per confident wrong answer (an answerable
    question answered wrongly, or an unanswerable one answered at all), 0 for a refusal.
    The weight 2 encodes the assumption that a wrong confident answer is worse than a refusal."""
    return s["correct"] - 2 * s["wrong_confident"] - 2 * (s["n_unanswerable"] - s["unanswerable_refused"])


def choose_threshold(rows, grid):
    """The threshold with the best utility on these rows; ties go to the highest (most cautious) one."""
    return max(grid, key=lambda t: (utility(summarise(rows, threshold=t)), t))


def cross_validate(rows, grid, folds=5):
    """k-fold estimate of the threshold step. Fold of row i = i % folds (no randomness).
    For each fold the threshold is chosen on the other folds and applied to the held-out fold.
    Returns the chosen thresholds and the held-out totals."""
    chosen, total = [], {"correct": 0, "wrong_confident": 0, "refused_by_mistake": 0, "unanswerable_refused": 0}
    for f in range(folds):
        train = [r for i, r in enumerate(rows) if i % folds != f]
        test = [r for i, r in enumerate(rows) if i % folds == f]
        t = choose_threshold(train, grid)
        s = summarise(test, threshold=t)
        chosen.append(t)
        for k in total:
            total[k] += s[k]
    return chosen, total
