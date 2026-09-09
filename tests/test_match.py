"""Company-matching regression tests.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from match import core, plausible, shares_token  # noqa: E402
from normalize import norm_company  # noqa: E402


class TestAutoAccept(unittest.TestCase):
    def assert_auto(self, a, b, expected, why):
        got = shares_token(core(norm_company(a)), core(norm_company(b)))
        self.assertEqual(got, expected, f"{a!r} vs {b!r}: {why}")

    def test_accepts_real_variants(self):
        self.assert_auto("Burns & McDonnell", "Burns McDonnell", True, "same firm")
        self.assert_auto("Jacobs", "Jacobs Engineering Group", True, "suffix only")
        self.assert_auto("Meta", "Meta Platforms", True, "suffix only")
        self.assert_auto("Google LLC", "Google (YouTube)", True, "same firm")

    def test_rejects_near_miss_names(self):
        # The one that shipped a wrong top-ranked card: both reduce to a single
        # near-identical token but they are unrelated companies.
        self.assert_auto("Dynamic Resources", "Dynamics Ventures LLC", False,
                         "different companies")
        self.assert_auto("ZGF Architects", "FGM Architects", False, "different firms")
        self.assert_auto("Bowman Consulting", "Grogan Consulting", False, "different firms")
        self.assert_auto("IQVIA", "Visa", False, "unrelated")
        self.assert_auto("Thermo Systems", "Hero", False, "unrelated")
        self.assert_auto("NBCUniversal", "Universal Management Solutions", False, "unrelated")

    def test_single_token_near_identity_is_askable_not_automatic(self):
        a, b = core(norm_company("Dynamic Resources")), core(norm_company("Dynamics Ventures"))
        self.assertTrue(plausible(a, b), "worth asking about")
        self.assertFalse(shares_token(a, b), "but never auto-accepted")


class TestNormalize(unittest.TestCase):
    def test_strips_trailing_noise_only(self):
        self.assertEqual(norm_company("The Rich Talent Group"), "rich talent")
        self.assertEqual(norm_company("Group Health"), "group health")

    def test_handles_separators_and_parens(self):
        self.assertEqual(norm_company("Acme - Northeast Region"), "acme")
        self.assertEqual(norm_company("Google (YouTube)"), "google")


if __name__ == "__main__":
    unittest.main()
