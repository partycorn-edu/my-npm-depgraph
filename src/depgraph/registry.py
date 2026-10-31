"""Клиент реестра npm на стандартной библиотеке (urllib)."""

import json
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .errors import NotFoundError, RepoError
from .semver import max_satisfying

ACCEPT_HEADER = "application/vnd.npm.install-v1+json"
USER_AGENT = "depgraph-study/1.0"
TIMEOUT_SECONDS = 20
HTTP_NOT_FOUND = 404
HINT_COUNT = 3
NETWORK_HINT = (
    "Проверьте сеть. Если реестр недоступен с вашего адреса, укажите в "
    "repository зеркало (например https://registry.npmmirror.com) или "
    "задайте прокси переменной HTTPS_PROXY."
)


def parse_json(body, url):
    """Разобрать тело ответа как JSON-объект."""
    try:
        data = json.loads(body)
    except ValueError:
        raise RepoError(f"ответ не является JSON: {url}") from None
    if not isinstance(data, dict):
        raise RepoError(f"ожидался JSON-объект: {url}")
    return data


def http_get_json(url, timeout=TIMEOUT_SECONDS):
    """Выполнить GET-запрос и вернуть JSON-объект из ответа."""
    request = Request(
        url,
        headers={"Accept": ACCEPT_HEADER, "User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
    except HTTPError as exc:
        if exc.code == HTTP_NOT_FOUND:
            raise NotFoundError(url) from None
        raise RepoError(
            f"сервер ответил {exc.code} {exc.reason}: {url}"
        ) from None
    except URLError as exc:
        raise RepoError(
            f"репозиторий недоступен ({exc.reason}): {url}. {NETWORK_HINT}"
        ) from None
    except (OSError, HTTPException) as exc:
        raise RepoError(
            f"сбой сети ({exc}): {url}. {NETWORK_HINT}"
        ) from None
    return parse_json(body, url)


class NpmRegistry:
    """Доступ к описаниям пакетов в реестре npm."""

    def __init__(self, base_url, fetch=http_get_json):
        """Запомнить адрес реестра и функцию загрузки JSON."""
        self.base_url = base_url.rstrip("/")
        self.fetch = fetch
        self.cache = {}

    def packument(self, name):
        """Вернуть описание пакета со всеми версиями (с кэшем)."""
        if name not in self.cache:
            self.cache[name] = self.load_packument(name)
        return self.cache[name]

    def load_packument(self, name):
        """Загрузить описание пакета из реестра."""
        url = f"{self.base_url}/{quote(name, safe='@')}"
        try:
            return self.fetch(url)
        except NotFoundError:
            raise RepoError(
                f"пакет '{name}' не найден в {self.base_url}"
            ) from None

    def versions(self, name):
        """Вернуть словарь версия -> описание версии."""
        versions = self.packument(name).get("versions")
        if not isinstance(versions, dict) or not versions:
            raise RepoError(f"у пакета '{name}' нет опубликованных версий")
        return versions

    def dependencies(self, name, version):
        """Вернуть прямые зависимости версии как словарь имя -> диапазон."""
        versions = self.versions(name)
        entry = versions.get(version)
        if not isinstance(entry, dict):
            latest = ", ".join(list(versions)[-HINT_COUNT:])
            raise RepoError(
                f"версия {version} пакета '{name}' не найдена, "
                f"последние версии: {latest}"
            )
        deps = entry.get("dependencies", {})
        if not isinstance(deps, dict):
            raise RepoError(f"неверное поле dependencies у {name}@{version}")
        return {str(key): str(value) for key, value in deps.items()}

    def resolve(self, name, spec):
        """Выбрать версию пакета под диапазон, точную версию или dist-tag."""
        versions = self.versions(name)
        if spec in versions:
            return spec
        tags = self.packument(name).get("dist-tags")
        if isinstance(tags, dict) and tags.get(spec) in versions:
            return tags[spec]
        try:
            found = max_satisfying(list(versions), spec)
        except ValueError:
            raise RepoError(
                f"не поддерживается спецификация '{spec}' пакета '{name}'"
            ) from None
        if found is None:
            raise RepoError(f"у пакета '{name}' нет версии под '{spec}'")
        return found
