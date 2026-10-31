"""Тесты командной строки с заглушкой реестра."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from depgraph.cli import main
from depgraph.errors import RepoError

TOML = (
    'package = "app"\n'
    'repository = "https://registry.npmjs.org"\n'
    'version = "1.0.0"\n'
)


class StubRegistry:
    """Заглушка реестра с фиксированными зависимостями."""

    deps = {"zeta": "^2.0.0", "alpha": "~1.1.0"}
    error = None

    def __init__(self, url):
        """Принять адрес реестра и ничего не делать."""

    def dependencies(self, name, version):
        """Вернуть заготовленные зависимости или выбросить ошибку."""
        if self.error:
            raise self.error
        return self.deps


def run_cli(args):
    """Запустить main и вернуть код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


@mock.patch("depgraph.cli.NpmRegistry", StubRegistry)
class CliTests(unittest.TestCase):
    """Проверки вывода и кодов выхода."""

    def make_config(self, text):
        """Создать временную конфигурацию и вернуть путь."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "config.toml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_tree_output(self):
        """Зависимости выводятся ASCII-деревом в алфавитном порядке."""
        code, out, _ = run_cli(["-c", self.make_config(TOML)])
        self.assertEqual(code, 0)
        self.assertIn("|-- alpha (~1.1.0)", out)
        self.assertIn("`-- zeta (^2.0.0)", out)
        self.assertNotIn("\x1b", out)

    def test_table_output(self):
        """При ascii_tree = false выводится таблица."""
        config = self.make_config(TOML + "ascii_tree = false\n")
        _, out, _ = run_cli(["-c", config])
        self.assertIn("Диапазон версий", out)
        self.assertNotIn("|-- ", out)

    def test_no_dependencies(self):
        """Пустой список зависимостей даёт предупреждение."""
        with mock.patch.object(StubRegistry, "deps", {}):
            code, out, _ = run_cli(["-c", self.make_config(TOML)])
        self.assertEqual(code, 0)
        self.assertIn("нет прямых зависимостей", out)

    def test_repo_error(self):
        """Ошибка репозитория даёт код 3 и сообщение в stderr."""
        with mock.patch.object(StubRegistry, "error", RepoError("сбой")):
            code, out, err = run_cli(["-c", self.make_config(TOML)])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("Ошибка репозитория: сбой", err)
        self.assertNotIn("Traceback", err)

    def test_config_error(self):
        """Ошибка конфигурации даёт код 2."""
        code, _, err = run_cli(["-c", "missing.toml"])
        self.assertEqual(code, 2)
        self.assertIn("Ошибка конфигурации", err)

    def test_test_mode_not_ready(self):
        """Тестовый режим на этом этапе сообщает о недоступности."""
        repo = Path(self.make_config("A:\n")).parent / "repo.txt"
        repo.write_text("A:\n", encoding="utf-8")
        text = (
            f'package = "A"\nrepository = "{repo}"\n'
            'version = "1"\ntest_mode = true\n'
        )
        code, _, err = run_cli(["-c", self.make_config(text)])
        self.assertEqual(code, 3)
        self.assertIn("этапе 3", err)


if __name__ == "__main__":
    unittest.main()
