"""Построчное описание ASCII-дерева зависимостей."""

from collections import namedtuple

TREE_MID = "|-- "
TREE_LAST = "`-- "
TREE_PIPE = "|   "
TREE_GAP = "    "
MARK_CYCLE = "cycle"
MARK_SEEN = "seen"

TreeLine = namedtuple("TreeLine", "prefix node mark")


def child_mark(graph, child, path, shown):
    """Определить пометку узла: цикл, повтор или None."""
    if child in path:
        return MARK_CYCLE
    if child in shown and graph.edges.get(child):
        return MARK_SEEN
    return None


def walk(graph, node, prefix, path, shown, lines):
    """Рекурсивно добавить строки потомков узла."""
    children = graph.edges.get(node, [])
    for child in children:
        is_last = child == children[-1]
        mark = child_mark(graph, child, path, shown)
        branch = TREE_LAST if is_last else TREE_MID
        lines.append(TreeLine(prefix + branch, child, mark))
        if mark is None:
            shown.add(child)
            deeper = prefix + (TREE_GAP if is_last else TREE_PIPE)
            walk(graph, child, deeper, path + (child,), shown, lines)


def tree_lines(graph):
    """Вернуть строки дерева без корня. Повторы и циклы не раскрываются."""
    lines = []
    walk(graph, graph.root, "", (graph.root,), {graph.root}, lines)
    return lines
