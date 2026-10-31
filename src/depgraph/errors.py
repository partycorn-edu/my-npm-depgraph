"""Ожидаемые ошибки приложения."""


class DepgraphError(Exception):
    """Базовая ожидаемая ошибка, для неё не нужна трассировка."""

    title = "Ошибка"
    exit_code = 1


class ConfigError(DepgraphError):
    """Ошибка конфигурационного файла."""

    title = "Ошибка конфигурации"
    exit_code = 2


class RepoError(DepgraphError):
    """Ошибка получения данных из репозитория."""

    title = "Ошибка репозитория"
    exit_code = 3


class NotFoundError(RepoError):
    """Репозиторий ответил, что запрошенного ресурса нет."""
