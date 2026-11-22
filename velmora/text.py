"""Tokenisation shared by indexing and querying. Pure stdlib."""
import re

STOPWORDS = frozenset("""
a an the is are am was were be been to of in on at for from with by and or if it its this that
these those do does did can could will would should i you your my me we our us they their what
when where which who how long much many there any get have has had need so as about after
until into than then also just
""".split())

_TOKEN = re.compile(r"\d+(?:[.,:]\d+)*%?|[a-z]+")


def _undouble(w: str) -> str:
    """cancelled -> cancel, shipped -> ship (but keep 'pass')."""
    return w[:-1] if len(w) > 3 and w[-1] == w[-2] and w[-1] != "s" else w


def stem(w: str) -> str:
    """Very light suffix stripper (deliberately simple, see NOTE.md)."""
    if w[0].isdigit():
        return w
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 5 and w.endswith("ing"):
        w = _undouble(w[:-3])
    elif len(w) > 4 and w.endswith("ed"):
        w = _undouble(w[:-2])
    elif len(w) > 4 and w.endswith(("ses", "xes", "zes", "ches", "shes")):
        w = w[:-2]
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    if len(w) > 4 and w.endswith("y"):  # delivery/deliver, delivered/delivery
        w = w[:-1]
    return w


def tokenize(text: str, drop_stopwords: bool = True) -> list:
    toks = _TOKEN.findall(text.lower().replace("\r", " "))
    if drop_stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    return [stem(t) for t in toks]


def split_sentences(text: str) -> list:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]
