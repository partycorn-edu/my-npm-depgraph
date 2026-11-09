"""Тесты загрузки и проверки конфигурации."""

import tempfile
import unittest
from pathlib import Path

from depgraph.config import load_config
from depgraph.errors import ConfigError

NPM_TOML = (
    'package = "express"\n'
    'repository = "https://registry.npmjs.org"\n'
    'version = "4.18.2"\n'
)


class ConfigTests(unittest.TestCase):
    """Проверки load_config на корректных и неверных файлах."""

    def setup(self):
        """Создать временный каталог для файлов конфигурации."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, text, name="config.toml"):
        """Записать файл во временный каталог и вернуть путь."""
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def assert_fails(self, text, fragment):
        """Проверить, что конфигурация даёт ConfigError с фрагментом."""
        with self.assertRaises(ConfigError) as ctx:
            load_config(self.write(text))
        self.assertIn(fragment, str(ctx.exception))

    def test_valid_with_defaults(self):
        """Необязательные параметры получают значения по умолчанию."""
        config = load_config(self.write(NPM_TOML))
        self.assertEqual(config.package, "express")
        self.assertFalse(config.test_mode)
        self.assertTrue(config.ascii_tree)

    def test_scoped_package(self):
        """Имена со скоупом разрешены."""
        text = NPM_TOML.replace("express", "@babel/core")
        self.assertEqual(load_config(self.write(text)).package, "@babel/core")

    def test_missing_file(self):
        """Отсутствующий файл даёт понятную ошибку."""
        with self.assertRaises(ConfigError):
            load_config(self.dir / "nope.toml")

    def test_directory_instead_of_file(self):
        """Каталог вместо файла даёт ошибку."""
        with self.assertRaises(ConfigError):
            load_config(self.dir)

    def test_bad_toml(self):
        """Синтаксическая ошибка TOML сообщается без трассировки."""
        self.assert_fails("package = [", "некорректный TOML")

    def test_missing_required(self):
        """Все отсутствующие обязательные ключи перечисляются."""
        self.assert_fails('version = "1.0.0"\n', "package, repository")

    def test_unknown_key(self):
        """Лишний ключ запрещён."""
        self.assert_fails(NPM_TOML + "color = 1\n", "color")

    def test_wrong_types(self):
        """Неверные типы значений отклоняются."""
        self.assert_fails(NPM_TOML + 'test_mode = "yes"\n', "test_mode")
        self.assert_fails(NPM_TOML.replace('"4.18.2"', "4"), "version")

    def test_empty_package(self):
        """Пустое имя пакета отклоняется."""
        self.assert_fails(NPM_TOML.replace("express", " "), "пустым")

    def test_bad_names(self):
        """Заглавные буквы и мусор недопустимы в имени npm-пакета."""
        self.assert_fails(NPM_TOML.replace("express", "Express"), "имя")
        self.assert_fails(NPM_TOML.replace("express", "a b"), "имя")

    def test_bad_url(self):
        """Допустимы только http и https."""
        self.assert_fails(NPM_TOML.replace("https", "ftp"), "URL")
        self.assert_fails(NPM_TOML.replace("https://", ""), "URL")

    def test_bad_version(self):
        """Версия должна быть точной."""
        for bad in ("4.18", "^4.18.2", "latest"):
            self.assert_fails(NPM_TOML.replace("4.18.2", bad), "версия")

    def test_test_mode_valid(self):
        """В тестовом режиме нужны файл и имя из больших букв."""
        repo = self.write("A: B\n", "repo.txt")
        text = (
            f'package = "A"\nrepository = "{repo}"\n'
            'version = "any"\ntest_mode = true\n'
        )
        config = load_config(self.write(text))
        self.assertTrue(config.test_mode)

    def test_test_mode_errors(self):
        """Тестовый режим проверяет имя и наличие файла."""
        repo = self.write("A: B\n", "repo.txt")
        base = f'repository = "{repo}"\nversion = "1"\ntest_mode = true\n'
        self.assert_fails('package = "a"\n' + base, "тестового режима")
        missing = base.replace("repo.txt", "none.txt")
        self.assert_fails('package = "A"\n' + missing, "не найден")
        folder = base.replace("repo.txt", "")
        self.assert_fails('package = "A"\n' + folder, "не файл")


if __name__ == "__main__":
    unittest.main()
