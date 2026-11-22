import unittest

from evaluation.metrics import (choose_threshold, cross_validate, judge_agreement, keywords_match, recall_at_k,
                                summarise, utility)


def row(answerable, abstained, ok=False, coverage=0.5, ranking=("KB-01",), sources=("KB-01",)):
    return {"answerable": answerable, "abstained": abstained, "keywords_ok": ok, "coverage": coverage,
            "ranking": list(ranking), "sources": list(sources) if answerable else []}


class TestRecall(unittest.TestCase):
    def test_hand_made_example(self):
        ranked = ["KB-03", "KB-06", "KB-09", "KB-01", "KB-02"]
        self.assertEqual(recall_at_k(ranked, ["KB-06"], 1), 0.0)   # right article is 2nd
        self.assertEqual(recall_at_k(ranked, ["KB-06"], 2), 1.0)
        self.assertEqual(recall_at_k(ranked, ["KB-02"], 5), 1.0)
        self.assertEqual(recall_at_k(ranked, ["KB-30"], 5), 0.0)   # not retrieved at all

    def test_two_source_questions_count_if_any_source_is_found(self):
        self.assertEqual(recall_at_k(["KB-12", "KB-03"], ["KB-12", "KB-13"], 1), 1.0)

    def test_undefined_without_sources(self):
        with self.assertRaises(ValueError):
            recall_at_k(["KB-01"], [], 1)


class TestKeywordJudge(unittest.TestCase):
    def test_ignores_case_and_spacing(self):
        self.assertTrue(keywords_match("It takes  3 TO 5\nworking days.", ["3 to 5 working days"]))

    def test_all_keywords_required(self):
        self.assertFalse(keywords_match("PayPal only", ["paypal", "sepa"]))
        self.assertTrue(keywords_match("PayPal or SEPA", ["paypal", "sepa"]))

    def test_no_keywords_never_matches(self):
        self.assertFalse(keywords_match("anything", []))


class TestSummary(unittest.TestCase):
    def test_counting_of_refusals_and_wrong_answers(self):
        rows = [row(True, False, ok=True),    # correct
                row(True, False, ok=False),   # wrong but confident
                row(True, True),              # refused by mistake
                row(False, True),             # correctly refused
                row(False, False)]            # unanswerable but answered
        s = summarise(rows)
        self.assertEqual((s["correct"], s["wrong_confident"], s["refused_by_mistake"], s["unanswerable_refused"]),
                         (1, 1, 1, 1))

    def test_threshold_recomputes_refusals_from_coverage(self):
        rows = [row(True, False, ok=True, coverage=0.4), row(False, False, coverage=0.2)]
        self.assertEqual(summarise(rows, threshold=0.3)["unanswerable_refused"], 1)
        self.assertEqual(summarise(rows, threshold=0.3)["correct"], 1)
        self.assertEqual(summarise(rows, threshold=0.5)["refused_by_mistake"], 1)


class TestJudgeAgreement(unittest.TestCase):
    def test_counts_both_kinds_of_disagreement_and_ignores_unreviewed(self):
        rows = [{"id": "A", "keywords_ok": True}, {"id": "B", "keywords_ok": True},
                {"id": "C", "keywords_ok": False}, {"id": "D", "keywords_ok": False}, {"id": "E", "keywords_ok": True}]
        human = {"A": True, "B": False, "C": True, "D": False}          # E is not reviewed
        self.assertEqual(judge_agreement(rows, human),
                         {"reviewed": 4, "agree": 2, "judge_too_generous": 1, "judge_too_strict": 1,
                          "correct_after_review": 2})


class TestThresholdChoice(unittest.TestCase):
    ROWS = [row(True, False, ok=True, coverage=0.9), row(True, False, ok=False, coverage=0.2),
            row(False, False, coverage=0.1), row(True, False, ok=True, coverage=0.8)]

    def test_utility_penalises_confident_wrong_answers_twice_as_much_as_a_correct_one_gains(self):
        s = summarise(self.ROWS, threshold=0.0)    # answers everything: 2 correct, 1 wrong, 1 unanswerable answered
        self.assertEqual(utility(s), 2 - 2 * 1 - 2 * 1)

    def test_best_threshold_refuses_the_low_coverage_questions(self):
        t = choose_threshold(self.ROWS, [0.0, 0.3, 0.95])
        self.assertEqual(t, 0.3)                   # 0.95 would also refuse the two correct answers

    def test_cross_validation_is_deterministic_and_chooses_one_threshold_per_fold(self):
        rows = self.ROWS * 5
        a = cross_validate(rows, [0.0, 0.3, 0.95])
        self.assertEqual(a, cross_validate(rows, [0.0, 0.3, 0.95]))
        self.assertEqual(len(a[0]), 5)
        self.assertEqual(a[1]["correct"], 10)          # 2 correct answers per copy of ROWS, none lost at 0.3


if __name__ == "__main__":
    unittest.main()
