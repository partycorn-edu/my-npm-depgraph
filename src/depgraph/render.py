"""Оформление вывода через rich."""

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

STYLE_TITLE = "bold cyan"
STYLE_DIM = "dim"
STYLE_OK = "bold green"
STYLE_WARN = "bold yellow"
STYLE_ERROR = "bold red"
STYLE_KEY = "cyan"


def make_console(plain, stderr=False):
    """Создать консоль. В режиме plain цвета и стили не выводятся."""
    return Console(
        stderr=stderr,
        color_system=None if plain else "auto",
        highlight=False,
    )


def box_style(console):
    """Выбрать рамки таблиц: ASCII без цвета, скруглённые в цвете."""
    return box.ASCII if console.color_system is None else box.ROUNDED


def format_value(value):
    """Показать значение параметра в синтаксисе TOML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def print_title(console, text):
    """Напечатать заголовок программы."""
    console.print(Text(text, style=STYLE_TITLE))


def print_ok(console, text):
    """Напечатать сообщение об успехе."""
    console.print(Text(text, style=STYLE_OK))


def print_warning(console, text):
    """Напечатать предупреждение."""
    console.print(Text(text, style=STYLE_WARN))


def print_error(console, title, message):
    """Напечатать ожидаемую ошибку без трассировки."""
    line = Text(f"{title}: ", style=STYLE_ERROR)
    line.append(message, style="red")
    console.print(line)


def print_config(console, config, source):
    """Напечатать параметры конфигурации таблицей ключ-значение."""
    print_title(console, "depgraph: граф зависимостей npm")
    console.print(Text(f"Конфигурация: {source}", style=STYLE_DIM))
    table = Table(
        title="Параметры",
        title_style=STYLE_TITLE,
        box=box_style(console),
    )
    table.add_column("Ключ", style=STYLE_KEY, no_wrap=True)
    table.add_column("Значение", overflow="fold")
    for key, value in config.as_pairs():
        table.add_row(Text(key), Text(format_value(value)))
    console.print(table)
    print_ok(console, "OK: конфигурация корректна")
