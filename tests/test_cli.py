"""Тесты командной строки."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from depgraph.cli import main

OK_TOML = (
    'package = "express"\n'
    'repository = "https://registry.npmjs.org"\n'
    'version = "4.18.2"\n'
)


def run_cli(args):
    """Запустить main и вернуть код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    """Проверки вывода и кодов выхода."""

    def make_config(self, text):
        """Создать временную конфигурацию и вернуть путь."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "config.toml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_prints_all_parameters(self):
        """Все параметры выводятся парами ключ-значение."""
        code, out, _ = run_cli(["-c", self.make_config(OK_TOML)])
        self.assertEqual(code, 0)
        for key in ("package", "repository", "test_mode", "version"):
            self.assertIn(key, out)
        self.assertIn("express", out)
        self.assertNotIn("\x1b", out)

    def test_error_has_no_traceback(self):
        """Ошибка конфигурации даёт код 2 и короткое сообщение."""
        code, out, err = run_cli(["-c", "missing.toml"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("Ошибка конфигурации", err)
        self.assertNotIn("Traceback", err)

    def test_no_color_flag(self):
        """Флаг --no-color не оставляет управляющих символов."""
        _, out, _ = run_cli(["--no-color", "-c", self.make_config(OK_TOML)])
        self.assertNotIn("\x1b", out)


if __name__ == "__main__":
    unittest.main()
