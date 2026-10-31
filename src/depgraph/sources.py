"""Источники графа: реестр npm и файл тестового репозитория."""

import re
from pathlib import Path

from .errors import RepoError
from .registry import NpmRegistry

LINE_RE = re.compile(r"^([A-Z]+)\s*:(.*)$")
NAME_RE = re.compile(r"^[A-Z]+$")
SEPARATORS_RE = re.compile(r"[\s,]+")
COMMENT_PREFIX = "#"
SHOW_LIMIT = 10


def make_node(name, version):
    """Собрать идентификатор узла npm-графа вида имя@версия."""
    return f"{name}@{version}"


def split_node(node):
    """Разобрать идентификатор узла на имя и версию."""
    name, _, version = node.rpartition("@")
    return name, version


class NpmSource:
    """Источник графа на основе реестра npm. Узлы имеют вид имя@версия."""

    def __init__(self, registry):
        """Запомнить клиент реестра."""
        self.registry = registry

    def children(self, node):
        """Вернуть узлы прямых зависимостей, диапазоны уже разрешены."""
        name, version = split_node(node)
        deps = self.registry.dependencies(name, version)
        return [self.child(node, dep, deps[dep]) for dep in sorted(deps)]

    def child(self, node, dep, spec):
        """Разрешить диапазон одной зависимости с понятным контекстом."""
        try:
            return make_node(dep, self.registry.resolve(dep, spec))
        except RepoError as exc:
            raise RepoError(f"{node} -> {dep} ({spec}): {exc}") from None

    def undefined(self, nodes):
        """В реестре все узлы известны, поэтому список пуст."""
        return []


def parse_line(number, line):
    """Разобрать строку вида 'A: B C' в пару (пакет, зависимости)."""
    match = LINE_RE.match(line)
    if not match:
        raise RepoError(
            f"строка {number}: ожидался формат 'A: B C', получено '{line}'"
        )
    deps = [dep for dep in SEPARATORS_RE.split(match.group(2)) if dep]
    for dep in deps:
        if not NAME_RE.match(dep):
            raise RepoError(
                f"строка {number}: имя '{dep}' должно состоять из "
                "больших латинских букв"
            )
    return match.group(1), list(dict.fromkeys(deps))


def parse_repository(text):
    """Разобрать текст тестового репозитория в словарь пакет -> зависимости."""
    table = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            continue
        name, deps = parse_line(number, line)
        if name in table:
            raise RepoError(f"строка {number}: пакет '{name}' описан дважды")
        table[name] = deps
    if not table:
        raise RepoError("тестовый репозиторий не содержит описаний пакетов")
    return table


class FileRepository:
    """Источник графа из файла тестового репозитория."""

    def __init__(self, table):
        """Запомнить словарь пакет -> зависимости."""
        self.table = table

    @classmethod
    def from_file(cls, path):
        """Прочитать и разобрать файл тестового репозитория."""
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RepoError(f"не удалось прочитать {path}: {exc}") from None
        return cls(parse_repository(text))

    def root(self, name):
        """Проверить, что корневой пакет описан в репозитории."""
        if name not in self.table:
            known = ", ".join(sorted(self.table)[:SHOW_LIMIT])
            raise RepoError(
                f"пакет '{name}' не описан в тестовом репозитории "
                f"(описаны: {known})"
            )
        return name

    def children(self, node):
        """Вернуть зависимости пакета, неописанный пакет считается листом."""
        return list(self.table.get(node, []))

    def undefined(self, nodes):
        """Найти пакеты, которые упомянуты, но не описаны."""
        return sorted(node for node in nodes if node not in self.table)


def open_source(config):
    """Создать источник по конфигурации и вернуть его вместе с корнем."""
    if config.test_mode:
        repository = FileRepository.from_file(config.repository)
        return repository, repository.root(config.package)
    source = NpmSource(NpmRegistry(config.repository))
    return source, make_node(config.package, config.version)
