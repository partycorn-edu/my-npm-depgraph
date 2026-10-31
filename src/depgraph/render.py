"""Оформление вывода через rich."""

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .tree import MARK_CYCLE, MARK_SEEN, tree_lines

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


def tree_line_text(line):
    """Собрать строку дерева с подсветкой узла и пометок."""
    text = Text(line.prefix, style=STYLE_DIM)
    text.append(line.node, style=STYLE_KEY)
    if line.mark == MARK_CYCLE:
        text.append(" (цикл)", style=STYLE_ERROR)
    elif line.mark == MARK_SEEN:
        text.append(" (повтор, поддерево выше)", style=STYLE_WARN)
    return text


def print_tree(console, graph):
    """Напечатать граф ASCII-деревом."""
    console.print(Text(graph.root, style="bold"))
    for line in tree_lines(graph):
        console.print(tree_line_text(line))


def print_adjacency(console, graph):
    """Напечатать граф таблицей: пакет и его прямые зависимости."""
    table = Table(box=box_style(console))
    table.add_column("Пакет", style=STYLE_KEY)
    table.add_column("Зависит от", overflow="fold")
    for node, children in graph.edges.items():
        table.add_row(Text(node), Text(", ".join(children) or "-"))
    console.print(table)


def print_cycles(console, cycles):
    """Напечатать найденные циклические зависимости."""
    if not cycles:
        return
    print_warning(console, f"Циклические зависимости: {len(cycles)}")
    for cycle in cycles:
        console.print(Text("  " + " -> ".join(cycle), style="red"))


def print_graph(console, graph, cycles, undefined, as_tree):
    """Напечатать граф, сводку, циклы и предупреждения."""
    print_title(console, f"depgraph: граф зависимостей {graph.root}")
    if as_tree:
        print_tree(console, graph)
    else:
        print_adjacency(console, graph)
    print_cycles(console, cycles)
    if undefined:
        names = ", ".join(undefined)
        print_warning(console, f"Не описаны, считаются листьями: {names}")
    print_ok(
        console,
        f"OK: пакетов {len(graph.edges)}, связей {graph.edge_count()}",
    )
