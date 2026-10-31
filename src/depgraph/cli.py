"""Точка входа командной строки."""

import argparse
import os
import sys

from .config import load_config
from .errors import DepgraphError
from .render import make_console, print_config, print_error

DEFAULT_CONFIG = "config.toml"
NO_COLOR_ENV = "NO_COLOR"
EXIT_OK = 0
EXIT_INTERRUPTED = 130

EPILOG = (
    "Параметры задаются в TOML-файле: package, repository, test_mode, "
    "version, ascii_tree. Пример: config.example.toml. "
    "Цвета отключаются флагом --no-color, переменной NO_COLOR "
    "или выводом не в терминал."
)


def build_parser():
    """Собрать разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Граф зависимостей пакета npm по TOML-конфигурации.",
        epilog=EPILOG,
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG,
        metavar="ФАЙЛ",
        help=f"путь к TOML-конфигурации (по умолчанию {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="отключить цвета и рамки Unicode",
    )
    return parser


def is_plain(stream, no_color_flag):
    """Понять, нужен ли вывод без цветов для данного потока."""
    if no_color_flag or os.environ.get(NO_COLOR_ENV):
        return True
    return not stream.isatty()


def main(argv=None):
    """Запустить приложение и вернуть код выхода."""
    args = build_parser().parse_args(argv)
    console = make_console(is_plain(sys.stdout, args.no_color))
    errors = make_console(is_plain(sys.stderr, args.no_color), stderr=True)
    try:
        config = load_config(args.config)
        print_config(console, config, args.config)
    except DepgraphError as exc:
        print_error(errors, exc.title, str(exc))
        return exc.exit_code
    except KeyboardInterrupt:
        print_error(errors, "Прервано", "работа остановлена пользователем")
        return EXIT_INTERRUPTED
    return EXIT_OK
