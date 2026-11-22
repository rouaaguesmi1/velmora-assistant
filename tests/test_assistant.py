import unittest
from pathlib import Path

from velmora.assistant import IDK, Assistant, disagree, figures
from velmora.kb import load_kb, parse_article

KB = Path(__file__).resolve().parent.parent / "data" / "kb"


class TestParsing(unittest.TestCase):
    def test_windows_line_endings(self):
        a = parse_article("---\r\nid: KB-99\r\ntitle: T\r\ncategory: C\r\nupdated: 2026-01-02\r\n---\r\n\r\n# T\r\n\r\nHello world.\r\n")
        self.assertEqual((a.id, a.body, a.updated.year), ("KB-99", "Hello world.", 2026))


class TestAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = Assistant(load_kb(KB))

    def test_unknown_subject_gives_idk_and_no_citation(self):
        r = self.a.answer("Do you have a physical shop in Lyon?")
        self.assertTrue(r.abstained)
        self.assertEqual((r.text, r.cited), (IDK, ()))

    def test_answers_with_text_copied_from_the_cited_article(self):
        r = self.a.answer("How many times can I retry a declined card payment?")
        self.assertEqual(r.cited, ("KB-03",))
        body = {a.id: a.body for a in load_kb(KB)}["KB-03"]
        for sentence in r.text.split(" [KB-")[0].split(". "):          # drop the "[KB-03, updated ...]" label
            self.assertIn(sentence.strip(". "), body)

    def test_two_articles_that_disagree_are_both_shown_with_their_dates(self):
        r = self.a.answer("How much does Express delivery cost?")      # KB-06 (2026) says 7.90, KB-07 (2022) says 9.90
        self.assertTrue(r.conflict)
        self.assertEqual(set(r.cited), {"KB-06", "KB-07"})
        for expected in ("7.90", "9.90", "2026-02-10", "2022-09-14", "inconsistent"):
            self.assertIn(expected, r.text)

    def test_conflicting_answers_are_listed_newest_first(self):
        r = self.a.answer("How much does Express delivery cost?")      # KB-07 ranks first but is the older one
        self.assertLess(r.text.index("2026-02-10"), r.text.index("2022-09-14"))
        self.assertLess(r.text.index("7.90"), r.text.index("9.90"))

    def test_no_conflict_note_when_articles_do_not_disagree(self):
        r = self.a.answer("How long is the password reset link valid?")
        self.assertFalse(r.conflict)
        self.assertEqual(len(r.cited), 1)

    def test_answer_sentence_is_the_one_that_tells_sentences_apart(self):
        r = self.a.answer("How long is a gift card valid?")             # was a wrong answer before the local weighting
        self.assertIn("24 months", r.text)


class TestFigures(unittest.TestCase):
    def test_same_unit_different_number_disagrees(self):
        self.assertTrue(disagree("Returns within 30 days.", "Sale items within 14 days."))
        self.assertTrue(disagree("It costs 7.90 EUR.", "It costs 9.90 EUR."))

    def test_different_units_or_same_figures_do_not_disagree(self):
        self.assertFalse(disagree("Refund within 5 business days.", "Return within 30 days."))
        self.assertFalse(disagree("Within 30 days.", "Within 30 days of delivery."))

    def test_ranges_are_one_figure(self):
        self.assertEqual(figures("Takes 3 to 5 working days."), {("3-5", "working")})


if __name__ == "__main__":
    unittest.main()
