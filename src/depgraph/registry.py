"""Клиент реестра npm на стандартной библиотеке (urllib)."""

import gzip
import json
import socket
import zlib
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import (
    ProxyHandler,
    Request,
    build_opener,
    getproxies,
    proxy_bypass,
)

from .errors import NotFoundError, RepoError
from .semver import max_satisfying

ACCEPT_HEADER = "application/vnd.npm.install-v1+json"
USER_AGENT = "depgraph-study/1.0"
TIMEOUT_SECONDS = 20
HTTP_NOT_FOUND = 404
HINT_COUNT = 3
MAX_WORKERS = 8
DEAD_PROXIES = set()
NETWORK_HINT = (
    "Проверьте прокси-переменные (HTTPS_PROXY) и что адрес реестра не "
    "разрешается в 127.0.0.1 или 0.0.0.0. Можно указать в repository "
    "зеркало, например https://registry.npmmirror.com."
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


def proxy_label(value):
    """Показать адрес прокси без логина и пароля."""
    return urlparse(value).netloc.rpartition("@")[2] or value


def used_proxy(url):
    """Вернуть адрес прокси из окружения для этого URL или None."""
    parts = urlparse(url)
    proxy = getproxies().get(parts.scheme)
    if proxy and not proxy_bypass(parts.hostname):
        return proxy_label(proxy)
    return None


def describe_network(url):
    """Собрать сведения для диагностики: прокси и адреса хоста."""
    lines = []
    host = urlparse(url).hostname
    proxy = used_proxy(url)
    if proxy:
        lines.append(
            f"Для этого адреса задан прокси {proxy}, при его отказе "
            "программа пробует прямое соединение."
        )
    try:
        found = {item[4][0] for item in socket.getaddrinfo(host, None)}
        lines.append(f"{host} разрешается в: {', '.join(sorted(found))}")
    except OSError as exc:
        lines.append(f"DNS не разрешил {host}: {exc}")
    return "\n".join(lines)


def network_error(reason, url):
    """Создать ошибку сети с диагностикой и подсказкой."""
    details = describe_network(url)
    return RepoError(f"{reason}: {url}\n{details}\n{NETWORK_HINT}")


def read_body(response):
    """Прочитать тело ответа и распаковать gzip, если он включён."""
    body = response.read()
    if response.headers.get("Content-Encoding") == "gzip":
        return gzip.decompress(body)
    return body


def make_request(url):
    """Создать новый запрос (после работы через прокси он непригоден)."""
    return Request(
        url,
        headers={
            "Accept": ACCEPT_HEADER,
            "Accept-Encoding": "gzip",
            "User-Agent": USER_AGENT,
        },
    )


def fetch_body(url, timeout, direct):
    """Выполнить запрос и вернуть тело. При direct прокси игнорируется."""
    opener = build_opener(ProxyHandler({})) if direct else build_opener()
    with opener.open(make_request(url), timeout=timeout) as response:
        return read_body(response)


def get_body(url, timeout):
    """Получить тело ответа, при отказе прокси повторить напрямую."""
    proxy = used_proxy(url)
    if proxy is None or proxy in DEAD_PROXIES:
        return fetch_body(url, timeout, True)
    try:
        return fetch_body(url, timeout, False)
    except HTTPError:
        raise
    except (OSError, HTTPException, EOFError, zlib.error):
        body = fetch_body(url, timeout, True)
        DEAD_PROXIES.add(proxy)
        return body


def http_get_json(url, timeout=TIMEOUT_SECONDS):
    """Выполнить GET-запрос и вернуть JSON-объект из ответа."""
    try:
        body = get_body(url, timeout)
    except HTTPError as exc:
        if exc.code == HTTP_NOT_FOUND:
            raise NotFoundError(url) from None
        raise RepoError(
            f"сервер ответил {exc.code} {exc.reason}: {url}"
        ) from None
    except URLError as exc:
        reason = f"репозиторий недоступен ({exc.reason})"
        raise network_error(reason, url) from None
    except (OSError, HTTPException, EOFError, zlib.error) as exc:
        raise network_error(f"сбой сети ({exc})", url) from None
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

    def prefetch(self, names):
        """Параллельно загрузить описания пакетов, которых нет в кэше."""
        missing = sorted({name for name in names if name not in self.cache})
        if not missing:
            return
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            loaded = list(pool.map(self.load_packument, missing))
        self.cache.update(zip(missing, loaded))

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
