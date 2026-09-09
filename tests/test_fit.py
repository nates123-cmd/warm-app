"""Fit-scoring regression tests.

Calibrated against jobs a real user had already saved by hand: those scored
57-78 (median 66). The bands exist to put her own picks in the top tier, so
these tests pin that relationship rather than the raw numbers.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from fit import HARD_REJECT, STRONG, WORTH, band, score  # noqa: E402

CRIT = {
    "titles_strong": ["associate creative director", "editorial director",
                      "brand copywriter", "senior copywriter"],
    "titles_target": ["copywriter", "editorial", "content strategist"],
    "titles_exclude": ["intern", "junior", "art", "art director", "engineer"],
    "seniority_target": ["Mid-Senior level", "Director"],
    "seniority_avoid": ["Internship", "Entry level"],
    "keywords_good": ["brand voice", "copywriting", "campaign", "editorial",
                      "storytelling", "content strategy", "social"],
    "keywords_bad": ["security clearance"],
    "min_salary": None,
    "workplace_pref": "any",
}

DESC = ("We are looking for a copywriter to own brand voice across campaign work, "
        "editorial storytelling, content strategy and social. ")


def s(title, **kw):
    job = {"title": title, "description": DESC, "location": "New York, NY"}
    job.update(kw)
    return score(job, CRIT)[0]


class TestBands(unittest.TestCase):
    def test_her_own_picks_land_in_the_top_tier(self):
        """The four jobs she had saved must not fall into 'weak'."""
        picks = [
            s("Associate Creative Director, Copywriter"),
            s("Editorial Director", seniority_level="Director"),
            s("Senior Associate, Senior Brand Copywriter"),
            s("VP, Associate Creative Director. Copy"),
        ]
        for fit in picks:
            self.assertGreaterEqual(fit, WORTH, "a hand-saved job scored as weak")
        self.assertGreaterEqual(max(picks), STRONG, "none of her picks reached strong")

    def test_band_boundaries(self):
        self.assertEqual(band(HARD_REJECT), "excluded")
        self.assertEqual(band(STRONG), "strong")
        self.assertEqual(band(WORTH), "worth a look")
        self.assertEqual(band(WORTH - 1), "weak")


class TestExclusions(unittest.TestCase):
    def test_art_direction_is_not_a_copy_role(self):
        # No comma, so "art director" never appears as a substring; the bare
        # token "art" is what catches it.
        self.assertEqual(s("Associate Creative Director Art"), HARD_REJECT)
        self.assertEqual(s("Associate Creative Director, Art"), HARD_REJECT)

    def test_word_boundary_does_not_overreach(self):
        """'art' inside 'Partnership' must not exclude the job."""
        self.assertNotEqual(s("Content Strategy Lead, Marketplace Partnership"),
                            HARD_REJECT)

    def test_hard_rejects(self):
        self.assertEqual(s("Copywriting Intern"), HARD_REJECT)
        self.assertEqual(s("Senior Copywriter", description=DESC + "security clearance required"),
                         HARD_REJECT)


class TestSignals(unittest.TestCase):
    def test_strong_title_outranks_loose_title(self):
        self.assertGreater(s("Senior Copywriter"), s("Copywriter"))

    def test_salary_floor_penalises_low_pay(self):
        crit = dict(CRIT, min_salary=120000)
        low = score({"title": "Senior Copywriter", "description": DESC,
                     "salary_min": 60000, "salary_max": 75000}, crit)[0]
        high = score({"title": "Senior Copywriter", "description": DESC,
                      "salary_min": 130000, "salary_max": 160000}, crit)[0]
        self.assertGreater(high, low)

    def test_unenriched_jobs_cannot_score_as_strong(self):
        """Title-only evidence must not masquerade as a confident match."""
        self.assertLess(s("Associate Creative Director", description=""), STRONG)

    def test_reasons_always_given(self):
        _, reasons = score({"title": "Senior Copywriter", "description": DESC}, CRIT)
        self.assertTrue(reasons, "a score with no explanation is not actionable")


if __name__ == "__main__":
    unittest.main()
