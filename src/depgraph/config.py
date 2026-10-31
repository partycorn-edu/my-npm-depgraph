"""Загрузка и проверка TOML-конфигурации."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import ConfigError

KEY_PACKAGE = "package"
KEY_REPOSITORY = "repository"
KEY_TEST_MODE = "test_mode"
KEY_VERSION = "version"
KEY_ASCII_TREE = "ascii_tree"

REQUIRED_KEYS = (KEY_PACKAGE, KEY_REPOSITORY, KEY_VERSION)
STRING_KEYS = (KEY_PACKAGE, KEY_REPOSITORY, KEY_VERSION)
BOOL_KEYS = (KEY_TEST_MODE, KEY_ASCII_TREE)
DEFAULTS = {KEY_TEST_MODE: False, KEY_ASCII_TREE: True}
ALL_KEYS = REQUIRED_KEYS + BOOL_KEYS

HTTP_SCHEMES = ("http", "https")
MAX_NAME_LENGTH = 214
NPM_NAME_RE = re.compile(
    r"^(@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$"
)
TEST_NAME_RE = re.compile(r"^[A-Z]+$")
VERSION_RE = re.compile(
    r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$"
)


@dataclass(frozen=True)
class Config:
    """Проверенные параметры, настраиваемые пользователем."""

    package: str
    repository: str
    test_mode: bool
    version: str
    ascii_tree: bool

    def as_pairs(self):
        """Вернуть параметры как пары ключ-значение в порядке задания."""
        return [
            (KEY_PACKAGE, self.package),
            (KEY_REPOSITORY, self.repository),
            (KEY_TEST_MODE, self.test_mode),
            (KEY_VERSION, self.version),
            (KEY_ASCII_TREE, self.ascii_tree),
        ]


def read_raw(path):
    """Прочитать TOML-файл и превратить сбои чтения в ConfigError."""
    try:
        with Path(path).open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"файл не найден: {path}") from None
    except IsADirectoryError:
        raise ConfigError(f"это каталог, а не файл: {path}") from None
    except UnicodeDecodeError:
        raise ConfigError(f"файл {path} не в кодировке UTF-8") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"некорректный TOML в {path}: {exc}") from None
    except OSError as exc:
        raise ConfigError(f"не удалось прочитать {path}: {exc}") from None


def check_keys(raw):
    """Проверить набор ключей: нет лишних, есть все обязательные."""
    unknown = sorted(set(raw) - set(ALL_KEYS))
    if unknown:
        known = ", ".join(ALL_KEYS)
        raise ConfigError(
            f"неизвестные параметры: {', '.join(unknown)} (допустимы: {known})"
        )
    missing = [key for key in REQUIRED_KEYS if key not in raw]
    if missing:
        names = ", ".join(missing)
        raise ConfigError(f"не заданы обязательные параметры: {names}")


def check_types(raw):
    """Проверить типы значений и что строки не пустые."""
    for key in STRING_KEYS:
        value = raw.get(key, "")
        if not isinstance(value, str):
            raise ConfigError(f"параметр {key} должен быть строкой")
        if not value.strip():
            raise ConfigError(f"параметр {key} не должен быть пустым")
    for key in BOOL_KEYS:
        if not isinstance(raw.get(key, False), bool):
            raise ConfigError(f"параметр {key} должен быть true или false")


def validate_package(name, test_mode):
    """Проверить имя пакета по правилам режима."""
    if test_mode:
        if not TEST_NAME_RE.match(name):
            raise ConfigError(
                f"имя пакета '{name}' не подходит для тестового режима, "
                "нужны большие латинские буквы, например A"
            )
        return
    if len(name) > MAX_NAME_LENGTH or not NPM_NAME_RE.match(name):
        raise ConfigError(f"некорректное имя npm-пакета: '{name}'")


def validate_repository(value, test_mode):
    """Проверить URL реестра или путь к файлу тестового репозитория."""
    if test_mode:
        path = Path(value)
        if not path.exists():
            raise ConfigError(f"файл тестового репозитория не найден: {value}")
        if not path.is_file():
            raise ConfigError(f"тестовый репозиторий не файл: {value}")
        return
    parts = urlparse(value)
    if parts.scheme not in HTTP_SCHEMES or not parts.netloc:
        raise ConfigError(
            f"repository должен быть URL вида https://registry.npmjs.org, "
            f"получено: '{value}'"
        )


def validate_version(value, test_mode):
    """Проверить точную версию. В тестовом режиме версия не используется."""
    if test_mode:
        return
    if not VERSION_RE.match(value):
        raise ConfigError(
            f"версия '{value}' не похожа на точную semver-версию, "
            "например 4.18.2"
        )


def load_config(path):
    """Прочитать файл, проверить все параметры и вернуть Config."""
    raw = read_raw(path)
    check_keys(raw)
    check_types(raw)
    data = {**DEFAULTS, **raw}
    for key in STRING_KEYS:
        data[key] = data[key].strip()
    test_mode = data[KEY_TEST_MODE]
    validate_package(data[KEY_PACKAGE], test_mode)
    validate_repository(data[KEY_REPOSITORY], test_mode)
    validate_version(data[KEY_VERSION], test_mode)
    return Config(**data)
