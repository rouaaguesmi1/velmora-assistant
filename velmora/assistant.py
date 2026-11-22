"""The assistant: retrieve -> decide whether to answer -> extract one or two sentences.

Everything the answer says is copied from the help-center articles, so nothing can be invented.
When two articles give different figures for the same question, both are shown, with their dates.
"""
import math
import re
from dataclasses import dataclass

from .bm25 import BM25
from .text import split_sentences, tokenize

IDK = "I don't know: the help center does not contain an answer to this question. Please contact customer support."
THRESHOLD = 0.30       # abstain if the top article covers less than 30% of the question's idf mass
MAX_SENTENCES = 2
CONFLICT_ARTICLES = 5  # only the first 5 retrieved articles are checked for contradictions
_RANGE = re.compile(r"(\d+) to (\d+)")
_FIGURE = re.compile(r"(\d+(?:[.,]\d+)?(?:-\d+)?)\s*(%|[a-z]+)")
SAME_QUESTION = 0.8    # the other article's best sentence must score at least 80% of the top one's


@dataclass(frozen=True)
class Answer:
    text: str          # the answer, or IDK
    cited: tuple       # article ids; empty when the assistant does not know
    abstained: bool
    coverage: float    # the abstention signal (kept so the harness can try other thresholds)
    ranking: tuple     # ((article_id, bm25_score), ...) best first
    draft: str = ""    # the text even when abstaining (only used by the threshold table)
    conflict: bool = False


def figures(sentence):
    """{(number, unit)} found in a sentence, e.g. {('7.90', 'eur'), ('14', 'days')}.
    'business days' and 'working days' count as their own unit ('business', 'working')."""
    text = _RANGE.sub(r"\1-\2", sentence.lower())
    return {(n.replace(",", "."), u) for n, u in _FIGURE.findall(text)}


def disagree(a, b):
    """Two sentences disagree if they give a different number for the same unit."""
    fa, fb = figures(a), figures(b)
    return any(u1 == u2 and n1 != n2 for n1, u1 in fa for n2, u2 in fb)


class Assistant:
    def __init__(self, kb, threshold=THRESHOLD):
        self.kb, self.threshold = kb, threshold
        # the title is repeated so that title words weigh more than body words
        self.index = BM25([tokenize((a.title + " ") * 2 + a.body) for a in kb])

    def retrieve(self, question, k=5):
        scores = self.index.scores(tokenize(question))
        order = sorted(range(len(self.kb)), key=lambda i: -scores[i])
        return [(self.kb[i].id, scores[i]) for i in order[:k]], order

    def _best(self, article, q_tokens, n, local=False):
        """The n sentences that share the most idf weight with the question (document order), and the best score."""
        q = set(q_tokens)
        sents = split_sentences(article.body)
        toks = [set(tokenize(x)) for x in sents]
        n_sents = len(sents)
        # weight a word by how rare it is among THIS article's sentences, so a word found in every
        # sentence ("gift card" in the gift-card article) cannot outweigh the one that tells sentences apart
        local_idf = lambda t: math.log(1 + (n_sents - sum(t in x for x in toks) + 0.5) / (sum(t in x for x in toks) + 0.5))
        weight = local_idf if local else self.index.idf
        scored = [(sum(weight(t) for t in q & toks[i]), i, s) for i, s in enumerate(sents)]
        best = sorted(scored, key=lambda x: (-x[0], x[1]))[:n]
        return " ".join(s for _, _, s in sorted(best, key=lambda x: x[1])), best[0][0]

    def _label(self, art):
        return f"[{art.id}, updated {art.updated.isoformat()}]"

    def answer(self, question):
        q = tokenize(question)
        ranking, order = self.retrieve(question)
        if not q or ranking[0][1] == 0:                     # nothing in the help center shares a word
            return Answer(IDK, (), True, 0.0, tuple(ranking))
        top = self.kb[order[0]]
        coverage = self.index.coverage(order[0], q)
        draft, _ = self._best(top, q, MAX_SENTENCES, local=True)
        cited, conflict = [top.id], False
        top_sentence, top_score = self._best(top, q, 1)
        top_terms = set(q) & set(tokenize(top_sentence))
        parts = [(top, draft)]                              # (article, text copied from it), rank order
        for i in order[1:CONFLICT_ARTICLES]:
            other = self.kb[i]
            if other.category != top.category:
                continue
            sentence, score = self._best(other, q, 1)
            same_question = (top_terms == set(q) and score >= SAME_QUESTION * top_score
                             and top_terms <= set(tokenize(sentence)))
            if score > 0 and same_question and disagree(top_sentence, sentence):
                parts.append((other, sentence))
                cited.append(other.id)
                conflict = True
        if conflict:
            # Neutral order: newest first, so a stale article never leads just because it ranked higher.
            # Newest is NOT declared right (a newer article can be an exception, e.g. the sale terms).
            parts.sort(key=lambda p: p[0].updated, reverse=True)
            text = "The help center is inconsistent here; its articles give different answers (newest first): " + \
                   " ".join(f"{t} {self._label(a)}" for a, t in parts)
        else:
            text = f"{draft} {self._label(top)}"
        if coverage < self.threshold:
            return Answer(IDK, (), True, coverage, tuple(ranking), text, conflict)
        return Answer(text, tuple(cited), False, coverage, tuple(ranking), text, conflict)
