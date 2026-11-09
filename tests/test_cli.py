"""Тесты командной строки: тестовый режим и npm на заглушке."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from depgraph.cli import EXIT_TOO_DEEP, main
from depgraph.registry import NpmRegistry
from test_registry import FakeFetch

NPM_TOML = (
    'package = "app"\n'
    'repository = "http://r"\n'
    'version = "1.0.0"\n'
)
PACKUMENTS = {
    "http://r/app": {
        "versions": {"1.0.0": {"dependencies": {"lib": "^1.0.0"}}}
    },
    "http://r/lib": {
        "versions": {"1.0.0": {}, "1.2.0": {"dependencies": {"app": "*"}}}
    },
}


def run_cli(args):
    """Запустить main и вернуть код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


def fake_registry(url):
    """Создать реестр, который читает данные из заглушки."""
    return NpmRegistry(url, FakeFetch(PACKUMENTS))


class CliTests(unittest.TestCase):
    """Проверки вывода и кодов выхода."""

    def setup(self):
        """Создать временный каталог."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def config(self, repo_text, extra="", package="A"):
        """Создать тестовый репозиторий и конфигурацию, вернуть путь."""
        repo = self.dir / "repo.txt"
        repo.write_text(repo_text, encoding="utf-8")
        text = (
            f'package = "{package}"\nrepository = "{repo}"\n'
            f'version = "1"\ntest_mode = true\n{extra}'
        )
        path = self.dir / "config.toml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_tree_in_test_mode(self):
        """Тестовый режим печатает дерево и сводку."""
        code, out, _ = run_cli(["-c", self.config("A: B C\nB: C\nC:\n")])
        self.assertEqual(code, 0)
        self.assertIn("|-- B\n|   `-- C\n`-- C\n", out)
        self.assertIn("пакетов 3, связей 3", out)
        self.assertNotIn("\x1b", out)

    def test_table_in_test_mode(self):
        """При ascii_tree = false печатается таблица смежности."""
        config = self.config("A: B\nB:\n", "ascii_tree = false\n")
        _, out, _ = run_cli(["-c", config])
        self.assertIn("Зависит от", out)
        self.assertNotIn("`-- ", out)

    def test_cycle_report(self):
        """Цикл помечается в дереве и перечисляется отдельно."""
        _, out, _ = run_cli(["-c", self.config("A: B\nB: A\n")])
        self.assertIn("A (цикл)", out)
        self.assertIn("A -> B -> A", out)

    def test_undefined_warning(self):
        """Неописанный пакет даёт предупреждение."""
        code, out, _ = run_cli(["-c", self.config("A: X\n")])
        self.assertEqual(code, 0)
        self.assertIn("Не описаны, считаются листьями: X", out)

    def test_repo_errors(self):
        """Ошибки тестового репозитория дают код 3 без трассировки."""
        for text, package in (("A B\n", "A"), ("A:\n", "Z")):
            with self.subTest(text=text, package=package):
                code, out, err = run_cli(["-c", self.config(text, "", package)])
                self.assertEqual((code, out), (3, ""))
                self.assertIn("Ошибка репозитория", err)
                self.assertNotIn("Traceback", err)

    def test_too_deep_graph(self):
        """Слишком глубокий граф даёт код 4 без трассировки."""
        size = 1500
        lines = [f"N{'A' * i}: N{'A' * (i + 1)}" for i in range(1, size)]
        config = self.config("\n".join(lines) + "\n", package="NA")
        code, _, err = run_cli(["-c", config])
        self.assertEqual(code, EXIT_TOO_DEEP)
        self.assertNotIn("Traceback", err)

    def test_config_error(self):
        """Ошибка конфигурации даёт код 2."""
        code, _, err = run_cli(["-c", "missing.toml"])
        self.assertEqual(code, 2)
        self.assertIn("Ошибка конфигурации", err)

    @mock.patch("depgraph.sources.NpmRegistry", fake_registry)
    def test_npm_mode(self):
        """Режим npm разрешает диапазоны и находит цикл."""
        path = self.dir / "npm.toml"
        path.write_text(NPM_TOML, encoding="utf-8")
        code, out, _ = run_cli(["-c", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("`-- lib@1.2.0\n    `-- app@1.0.0 (цикл)", out)
        self.assertIn("app@1.0.0 -> lib@1.2.0 -> app@1.0.0", out)

    @mock.patch("depgraph.sources.NpmRegistry", fake_registry)
    def test_npm_unknown_package(self):
        """Неизвестный корневой пакет даёт код 3."""
        path = self.dir / "npm.toml"
        path.write_text(NPM_TOML.replace("app", "nope"), encoding="utf-8")
        code, _, err = run_cli(["-c", str(path)])
        self.assertEqual(code, 3)
        self.assertIn("не найден", err)


if __name__ == "__main__":
    unittest.main()
