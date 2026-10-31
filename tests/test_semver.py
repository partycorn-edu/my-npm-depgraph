"""Тесты разбора semver-диапазонов."""

import unittest

from depgraph.semver import max_satisfying

VERSIONS = [
    "0.0.3", "0.0.4", "0.1.0", "0.2.5", "0.3.0", "1.0.0", "1.2.3",
    "1.2.9", "1.3.0", "2.0.0", "2.1.0", "3.0.0-beta.1",
]

CASES = {
    "^1.2.3": "1.3.0",
    "^1.0.0": "1.3.0",
    "^0.2.5": "0.2.5",
    "^0.0.3": "0.0.3",
    "^0": "0.3.0",
    "^5": None,
    "~1.2.3": "1.2.9",
    "~1.2": "1.2.9",
    "~1": "1.3.0",
    ">=1.2.9": "2.1.0",
    ">= 1.2.9": "2.1.0",
    ">1.2.9 <2.1.0": "2.0.0",
    ">2": None,
    "<2": "1.3.0",
    "<1.0.0": "0.3.0",
    "<=1.2": "1.2.9",
    "1.x": "1.3.0",
    "1.2": "1.2.9",
    "*": "2.1.0",
    "": "2.1.0",
    "=1.2.3": "1.2.3",
    "v1.2.3": "1.2.3",
    "1.2.3 - 2.0.0": "2.0.0",
    "1.2.3 - 2": "2.1.0",
    "^1.0.0 || ^0.2.0": "1.3.0",
    "^7 || ^0.2.0": "0.2.5",
}


class SemverTests(unittest.TestCase):
    """Проверки выбора версии под диапазон."""

    def test_ranges(self):
        """Диапазоны дают ожидаемую наибольшую стабильную версию."""
        for spec, expected in CASES.items():
            with self.subTest(spec=spec):
                self.assertEqual(max_satisfying(VERSIONS, spec), expected)

    def test_prerelease_is_skipped(self):
        """Предрелизы не выбираются автоматически."""
        self.assertEqual(max_satisfying(["1.0.0", "2.0.0-rc.1"], "*"), "1.0.0")

    def test_unsupported_specs(self):
        """Теги, URL и алиасы не разбираются и дают ValueError."""
        for spec in ("latest", "git+https://x/y.git", "npm:foo@1", "file:../a"):
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    max_satisfying(VERSIONS, spec)


if __name__ == "__main__":
    unittest.main()
