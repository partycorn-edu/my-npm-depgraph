"""Тесты клиента реестра: заглушки и локальный HTTP-сервер."""

import gzip
import json
import os
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, HTTPServer

from depgraph import registry
from depgraph.errors import NotFoundError, RepoError
from depgraph.registry import NpmRegistry, http_get_json

PACKUMENT = {
    "versions": {
        "1.0.0": {"dependencies": {"left": "^1.0.0", "right": "~2.1.0"}},
        "1.1.0": {},
    }
}


class FakeFetch:
    """Заглушка загрузки JSON, считает обращения."""

    def __init__(self, data):
        """Запомнить ответы по URL."""
        self.data = data
        self.calls = []

    def __call__(self, url):
        """Вернуть данные или имитировать ответ 404."""
        self.calls.append(url)
        if url not in self.data:
            raise NotFoundError(url)
        return self.data[url]


class RegistryTests(unittest.TestCase):
    """Проверки NpmRegistry на заглушке."""

    def setup(self):
        """Создать реестр с одной заглушкой пакета."""
        self.fetch = FakeFetch({"http://r/pkg": PACKUMENT})
        self.registry = NpmRegistry("http://r/", self.fetch)

    def test_direct_dependencies(self):
        """Возвращаются прямые зависимости нужной версии."""
        deps = self.registry.dependencies("pkg", "1.0.0")
        self.assertEqual(deps, {"left": "^1.0.0", "right": "~2.1.0"})

    def test_no_dependencies_field(self):
        """Отсутствие поля dependencies даёт пустой словарь."""
        self.assertEqual(self.registry.dependencies("pkg", "1.1.0"), {})

    def test_prefetch(self):
        """Prefetch загружает недостающее один раз и заполняет кэш."""
        self.registry.prefetch(["pkg", "pkg"])
        self.registry.prefetch(["pkg"])
        self.assertEqual(len(self.fetch.calls), 1)
        self.assertIn("pkg", self.registry.cache)

    def test_cache(self):
        """Описание пакета запрашивается один раз."""
        self.registry.dependencies("pkg", "1.0.0")
        self.registry.dependencies("pkg", "1.1.0")
        self.assertEqual(len(self.fetch.calls), 1)

    def test_unknown_package(self):
        """Неизвестный пакет даёт понятную ошибку."""
        with self.assertRaises(RepoError) as ctx:
            self.registry.dependencies("zzz", "1.0.0")
        self.assertIn("не найден", str(ctx.exception))

    def test_unknown_version(self):
        """Неизвестная версия даёт ошибку с подсказкой."""
        with self.assertRaises(RepoError) as ctx:
            self.registry.dependencies("pkg", "9.9.9")
        self.assertIn("1.1.0", str(ctx.exception))

    def test_scoped_name_in_url(self):
        """Имя со скоупом кодируется в URL."""
        fetch = FakeFetch({"http://r/@a%2Fb": PACKUMENT})
        registry = NpmRegistry("http://r", fetch)
        registry.dependencies("@a/b", "1.1.0")
        self.assertEqual(fetch.calls, ["http://r/@a%2Fb"])

    def test_bad_structure(self):
        """Некорректная структура ответа отклоняется."""
        fetch = FakeFetch({"http://r/bad": {"versions": []}})
        with self.assertRaises(RepoError):
            NpmRegistry("http://r", fetch).dependencies("bad", "1.0.0")


class Handler(BaseHTTPRequestHandler):
    """Локальный сервер с несколькими типами ответов."""

    def handle_get(self):
        """Ответить в зависимости от пути."""
        routes = {
            "/ok": (200, json.dumps({"a": 1}).encode()),
            "/text": (200, b"not json"),
            "/list": (200, b"[1, 2]"),
            "/err": (500, b"oops"),
            "/gz": (200, gzip.compress(b'{"zipped": true}')),
        }
        code, body = routes.get(self.path, (404, b"{}"))
        self.send_response(code)
        if self.path == "/gz":
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        """Не печатать журнал запросов."""


setattr(Handler, "do_GET", Handler.handle_get)


class HttpTests(unittest.TestCase):
    """Проверки http_get_json на локальном сервере."""

    @classmethod
    def setup_class(cls):
        """Запустить сервер на свободном порту."""
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def teardown_class(cls):
        """Остановить сервер."""
        cls.server.shutdown()
        cls.server.server_close()

    def test_ok(self):
        """Корректный JSON возвращается как словарь."""
        self.assertEqual(http_get_json(self.base + "/ok"), {"a": 1})

    def test_gzip(self):
        """Ответ со сжатием gzip распаковывается."""
        self.assertEqual(http_get_json(self.base + "/gz"), {"zipped": True})

    def test_not_found(self):
        """Ответ 404 превращается в NotFoundError."""
        with self.assertRaises(NotFoundError):
            http_get_json(self.base + "/none")

    def test_server_error(self):
        """Ответ 500 превращается в RepoError."""
        with self.assertRaises(RepoError):
            http_get_json(self.base + "/err")

    def test_not_json(self):
        """Не-JSON и не-объект отклоняются."""
        for path in ("/text", "/list"):
            with self.assertRaises(RepoError):
                http_get_json(self.base + path)

    def test_dead_proxy_falls_back_to_direct(self):
        """Если прокси отказывает, запрос повторяется напрямую."""
        env = {"HTTP_PROXY": "http://127.0.0.1:9"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(registry, "DEAD_PROXIES", set()) as dead:
                data = http_get_json(self.base + "/ok")
                again = http_get_json(self.base + "/ok")
        self.assertEqual((data, again), ({"a": 1}, {"a": 1}))
        self.assertEqual(dead, {"127.0.0.1:9"})

    def test_proxy_and_direct_both_fail(self):
        """Если не работает и прямое соединение, это RepoError."""
        env = {"HTTP_PROXY": "http://127.0.0.1:9"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(registry, "DEAD_PROXIES", set()) as dead:
                with self.assertRaises(RepoError) as ctx:
                    http_get_json("http://127.0.0.1:9/x", timeout=2)
        self.assertEqual(dead, set())
        self.assertIn("задан прокси 127.0.0.1:9", str(ctx.exception))

    def test_connection_refused(self):
        """Недоступный порт даёт RepoError, а не исключение сокета."""
        with self.assertRaises(RepoError) as ctx:
            http_get_json("http://127.0.0.1:9/x", timeout=2)
        self.assertIn("зеркало", str(ctx.exception))
        self.assertIn("127.0.0.1 разрешается в: 127.0.0.1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
