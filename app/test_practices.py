"""Small contract checks for the curated, paid Intima practices."""

import unittest

from app.practices import PRACTICE_COST, PRACTICES, PRACTICES_BY_ID, SELF_DISCOVERY_WARNING


class PracticeCatalogTests(unittest.TestCase):
    def test_catalog_has_ten_unique_practices_with_steps(self) -> None:
        self.assertEqual(len(PRACTICES), 10)
        self.assertEqual(len(PRACTICES_BY_ID), 10)
        self.assertEqual(PRACTICE_COST, 1)
        for practice in PRACTICES:
            self.assertIn(practice["id"], PRACTICES_BY_ID)
            self.assertTrue(practice["title"])
            self.assertGreaterEqual(len(practice["steps"]), 3)

    def test_self_discovery_practices_include_the_safety_warning(self) -> None:
        self_practices = [practice for practice in PRACTICES if practice["collection"] == "self"]
        self.assertEqual(len(self_practices), 5)
        self.assertTrue(all(practice["warning"] == SELF_DISCOVERY_WARNING for practice in self_practices))


if __name__ == "__main__":
    unittest.main()
