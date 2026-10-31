"""Построение графа зависимостей: BFS с рекурсией и поиск циклов."""

from dataclasses import dataclass


@dataclass
class Graph:
    """Граф зависимостей. Ключи edges идут в порядке обхода BFS."""

    root: str
    edges: dict

    def edge_count(self):
        """Вернуть общее число связей между пакетами."""
        return sum(len(children) for children in self.edges.values())


def skip_level(level, done):
    """Обработчик прогресса по умолчанию, ничего не делает."""


def expand_level(source, level, edges, seen, on_level):
    """Обработать один уровень BFS и рекурсивно перейти к следующему."""
    if not level:
        return
    next_level = []
    on_level(level, len(edges))
    source.prepare(level)
    for node in level:
        children = source.children(node)
        edges[node] = children
        for child in children:
            if child not in seen:
                seen.add(child)
                next_level.append(child)
    expand_level(source, next_level, edges, seen, on_level)


def build_graph(source, root, on_level=None):
    """Построить граф от корня. Уже встреченные узлы не раскрываются.

    Функция on_level(уровень, число_обработанных) вызывается перед
    загрузкой данных очередного уровня и нужна для показа прогресса.
    """
    edges = {}
    expand_level(source, [root], edges, {root}, on_level or skip_level)
    return Graph(root, edges)


def visit(graph, node, path, done, cycles):
    """Обход в глубину, ребро в узел текущего пути даёт цикл."""
    path.append(node)
    for child in graph.edges.get(node, []):
        if child in path:
            cycles.append(path[path.index(child):] + [child])
        elif child not in done:
            visit(graph, child, path, done, cycles)
    path.pop()
    done.add(node)


def find_cycles(graph):
    """Найти циклы как списки узлов, первый и последний узел совпадают."""
    cycles = []
    visit(graph, graph.root, [], set(), cycles)
    return cycles
