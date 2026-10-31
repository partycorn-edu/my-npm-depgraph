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
TREE_MID = "|-- "
TREE_LAST = "`-- "


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


def tree_text(prefix, name, spec):
    """Собрать строку дерева: ветка, имя пакета и диапазон версий."""
    line = Text(prefix, style=STYLE_DIM)
    line.append(name, style=STYLE_KEY)
    line.append(f" ({spec})", style=STYLE_WARN)
    return line


def print_dependency_tree(console, root, deps):
    """Напечатать прямые зависимости ASCII-деревом."""
    console.print(Text(root, style="bold"))
    names = sorted(deps)
    for name in names:
        prefix = TREE_LAST if name == names[-1] else TREE_MID
        console.print(tree_text(prefix, name, deps[name]))


def print_dependency_table(console, deps):
    """Напечатать прямые зависимости таблицей."""
    table = Table(box=box_style(console))
    table.add_column("Пакет", style=STYLE_KEY)
    table.add_column("Диапазон версий")
    for name in sorted(deps):
        table.add_row(Text(name), Text(deps[name]))
    console.print(table)


def print_dependencies(console, name, version, deps, as_tree):
    """Напечатать прямые зависимости пакета в выбранном виде."""
    root = f"{name}@{version}"
    print_title(console, f"depgraph: прямые зависимости {root}")
    if not deps:
        print_warning(console, "У этой версии нет прямых зависимостей")
        return
    if as_tree:
        print_dependency_tree(console, root, deps)
    else:
        print_dependency_table(console, deps)
    print_ok(console, f"Всего прямых зависимостей: {len(deps)}")
