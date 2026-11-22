"""Minimal BM25 (Okapi) with the helpers the abstention logic needs."""
import math
from collections import Counter


class BM25:
    def __init__(self, docs_tokens, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(d) for d in docs_tokens]
        self.lens = [len(d) for d in docs_tokens]
        self.avgdl = sum(self.lens) / len(self.lens)
        self.n = len(docs_tokens)
        self.df = Counter(t for d in self.docs for t in d)

    def idf(self, term):
        # An unseen term gets the maximum idf: an out-of-vocabulary word is evidence
        # that the help center does not talk about the question's subject.
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def scores(self, query_tokens):
        out = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in set(query_tokens):
                f = d.get(t, 0)
                if f:
                    s += self.idf(t) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avgdl))
            out.append(s)
        return out

    def coverage(self, doc_index, query_tokens):
        """Share of the query's idf mass found in one document, in [0, 1]."""
        qs = set(query_tokens)
        total = sum(self.idf(t) for t in qs)
        if total == 0:
            return 0.0
        return sum(self.idf(t) for t in qs if t in self.docs[doc_index]) / total
