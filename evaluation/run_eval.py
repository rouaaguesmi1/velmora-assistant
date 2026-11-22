"""One command:  python -m evaluation.run_eval"""
import argparse
import csv
import json
from pathlib import Path

from velmora.assistant import THRESHOLD, Assistant
from velmora.kb import load_kb
from .metrics import cross_validate, judge_agreement, keywords_match, summarise

ROOT = Path(__file__).resolve().parent.parent


def load_questions(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(assistant, questions):
    rows = []
    for q in questions:
        a = assistant.answer(q["question"])
        rows.append({
            "id": q["id"], "question": q["question"], "answerable": q["answerable"],
            "sources": q["source_articles"], "keywords": q["answer_keywords"],
            "ranking": [i for i, _ in a.ranking], "coverage": round(a.coverage, 3),
            "abstained": a.abstained, "answer": a.text, "cited": list(a.cited),
            # judged on the drafted text so that the threshold table can re-use it
            "keywords_ok": q["answerable"] and keywords_match(a.draft, q["answer_keywords"]),
        })
    return rows


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--kb", default=str(ROOT / "data" / "kb"))
    p.add_argument("--eval", default=str(ROOT / "data" / "eval.jsonl"))
    p.add_argument("--out", default=str(ROOT / "results"))
    p.add_argument("--review", default=str(ROOT / "data" / "manual_review.csv"))
    p.add_argument("--threshold", type=float, default=THRESHOLD)
    a = p.parse_args(argv)

    rows = evaluate(Assistant(load_kb(a.kb), threshold=a.threshold), load_questions(a.eval))
    s = summarise(rows)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    na, nu = s["n_answerable"], s["n_unanswerable"]
    pct = lambda x: f"{100 * x:.1f}%"
    print(f"Velmora assistant | threshold {a.threshold} | {na} answerable + {nu} unanswerable questions")
    print(f"recall@1: {pct(s['recall@1'])}   recall@3: {pct(s['recall@3'])}   recall@5: {pct(s['recall@5'])}   (answerable only)")
    print(f"correct answers (answerable):          {s['correct']}/{na} = {pct(s['correct'] / na)}")
    print(f"  wrong but confident:                 {s['wrong_confident']}/{na}")
    print(f"  refused by mistake:                  {s['refused_by_mistake']}/{na}")
    print(f"unanswerable correctly refused:        {s['unanswerable_refused']}/{nu}")
    print("\nWhat the 'I don't know' threshold does (same answers, different cut-off):")
    print("  threshold  correct  wrong_confident  refused_by_mistake  unanswerable_refused")
    for t in [round(0.05 * i, 2) for i in range(0, 15)]:
        x = summarise(rows, threshold=t)
        print(f"  {t:9.2f}  {x['correct']:7d}  {x['wrong_confident']:15d}  {x['refused_by_mistake']:18d}  {x['unanswerable_refused']:20d}")

    grid = [round(0.05 * i, 2) for i in range(0, 15)]
    chosen, cv = cross_validate(rows, grid)
    print(f"\n5-fold cross-validation of the threshold choice (chosen on 4/5 of the questions, applied to the other 1/5):")
    print(f"  thresholds chosen: {chosen}")
    print(f"  held-out totals: correct {cv['correct']}/{na}, wrong confident {cv['wrong_confident']}, "
          f"refused by mistake {cv['refused_by_mistake']}, unanswerable refused {cv['unanswerable_refused']}/{nu}")

    # judge check: write the sheet to fill in, and compare when it has been filled in
    with open(out / "review_template.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "question", "answer", "judge_correct", "human_correct"])
        for r in rows:
            if r["answerable"] and not r["abstained"]:
                w.writerow([r["id"], r["question"], r["answer"], int(r["keywords_ok"]), ""])
    review = Path(a.review)
    human = {}
    if review.exists():
        for r in csv.DictReader(open(review, encoding="utf-8")):
            v = (r.get("human_correct") or "").strip().lower()
            if v in ("y", "n", "1", "0"):
                human[r["id"]] = v in ("y", "1")
    if human:
        j = judge_agreement(rows, human)
        print(f"\njudge vs manual review ({j['reviewed']} answers reviewed): agree {j['agree']}, "
              f"judge too generous {j['judge_too_generous']}, judge too strict {j['judge_too_strict']}; "
              f"correct after review: {j['correct_after_review']}/{j['reviewed']}")
    else:
        print(f"\njudge vs manual review: not done. Fill the last column of {out / 'review_template.csv'} (y/n), "
              f"save it as data/manual_review.csv and run again.")
    print(f"\nper-question results: {out / 'results.jsonl'}")


if __name__ == "__main__":
    main()
