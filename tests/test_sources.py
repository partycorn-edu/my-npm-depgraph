"""Тесты источников: тестовый репозиторий и npm на заглушке."""

import tempfile
import unittest
from pathlib import Path

from depgraph.errors import RepoError
from depgraph.graph import build_graph, find_cycles
from depgraph.registry import NpmRegistry
from depgraph.sources import (
    FileRepository,
    NpmSource,
    make_node,
    parse_repository,
    split_node,
)
from test_registry import FakeFetch


def version_entry(**deps):
    """Собрать описание версии с зависимостями."""
    return {"dependencies": deps}


PACKUMENTS = {
    "http://r/app": {"versions": {"1.0.0": version_entry(lib="^1.0.0")}},
    "http://r/lib": {
        "dist-tags": {"latest": "2.0.0"},
        "versions": {
            "1.0.0": version_entry(),
            "1.5.0": version_entry(app="^1.0.0"),
            "2.0.0": version_entry(),
        },
    },
}


class ParseTests(unittest.TestCase):
    """Проверки разбора формата тестового репозитория."""

    def test_format(self):
        """Допускаются комментарии, запятые, пустые строки и дубликаты."""
        table = parse_repository("# c\n\nA: B, C B\nB:\nC :\n")
        self.assertEqual(table, {"A": ["B", "C"], "B": [], "C": []})

    def test_errors(self):
        """Неверные строки дают ошибку с номером строки."""
        cases = {
            "A B": "строка 1",
            "A: b": "строка 1",
            "a: B": "строка 1",
            "A: B\nA: C": "строка 2",
            "# only": "не содержит",
        }
        for text, fragment in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(RepoError) as ctx:
                    parse_repository(text)
                self.assertIn(fragment, str(ctx.exception))


class FileRepositoryTests(unittest.TestCase):
    """Проверки FileRepository."""

    def test_from_file_and_root(self):
        """Файл читается, корень проверяется, неописанные узлы находятся."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "repo.txt"
            path.write_text("A: B X\nB:\n", encoding="utf-8")
            repo = FileRepository.from_file(path)
        self.assertEqual(repo.root("A"), "A")
        self.assertEqual(repo.children("X"), [])
        self.assertEqual(repo.undefined(["A", "B", "X"]), ["X"])
        with self.assertRaises(RepoError):
            repo.root("Z")

    def test_unreadable(self):
        """Отсутствующий файл даёт RepoError."""
        with self.assertRaises(RepoError):
            FileRepository.from_file("no/such/file.txt")


class NpmSourceTests(unittest.TestCase):
    """Проверки NpmSource на заглушке реестра."""

    def make_source(self):
        """Создать источник поверх заглушки."""
        return NpmSource(NpmRegistry("http://r", FakeFetch(PACKUMENTS)))

    def test_node_helpers(self):
        """Идентификатор узла разбирается и для имён со скоупом."""
        node = make_node("@a/b", "1.0.0")
        self.assertEqual(split_node(node), ("@a/b", "1.0.0"))

    def test_range_resolution_and_cycle(self):
        """Диапазон разрешается в наибольшую версию, цикл находится."""
        graph = build_graph(self.make_source(), "app@1.0.0")
        self.assertEqual(
            graph.edges,
            {"app@1.0.0": ["lib@1.5.0"], "lib@1.5.0": ["app@1.0.0"]},
        )
        self.assertEqual(len(find_cycles(graph)), 1)

    def test_prepare_loads_everything_up_front(self):
        """После prepare обход графа не делает новых запросов."""
        fetch = FakeFetch(PACKUMENTS)
        source = NpmSource(NpmRegistry("http://r", fetch))
        source.prepare(["app@1.0.0"])
        calls = len(fetch.calls)
        self.assertEqual(calls, 2)
        source.children("app@1.0.0")
        self.assertEqual(len(fetch.calls), calls)

    def test_resolve_variants(self):
        """Точная версия, dist-tag и диапазон разрешаются."""
        registry = NpmRegistry("http://r", FakeFetch(PACKUMENTS))
        self.assertEqual(registry.resolve("lib", "1.0.0"), "1.0.0")
        self.assertEqual(registry.resolve("lib", "latest"), "2.0.0")
        self.assertEqual(registry.resolve("lib", "^1"), "1.5.0")

    def test_resolve_errors(self):
        """Неподходящий диапазон и неподдерживаемая спецификация."""
        registry = NpmRegistry("http://r", FakeFetch(PACKUMENTS))
        for spec in ("^9.0.0", "git+https://x/y.git"):
            with self.subTest(spec=spec):
                with self.assertRaises(RepoError):
                    registry.resolve("lib", spec)

    def test_error_has_context(self):
        """Ошибка разрешения зависимости называет узел и зависимость."""
        packuments = dict(PACKUMENTS)
        packuments["http://r/app"] = {
            "versions": {"1.0.0": version_entry(lib="^9.0.0")}
        }
        source = NpmSource(NpmRegistry("http://r", FakeFetch(packuments)))
        with self.assertRaises(RepoError) as ctx:
            source.children("app@1.0.0")
        self.assertIn("app@1.0.0 -> lib", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
