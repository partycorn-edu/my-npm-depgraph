"""Тесты построения графа, поиска циклов и дерева."""

import unittest

from depgraph.graph import build_graph, find_cycles
from depgraph.tree import MARK_CYCLE, MARK_SEEN, tree_lines


class DictSource:
    """Источник графа из словаря, считает вызовы children."""

    def __init__(self, table):
        """Запомнить словарь узел -> потомки."""
        self.table = table
        self.calls = []

    def prepare(self, level):
        """Подготовка не нужна."""

    def children(self, node):
        """Вернуть потомков узла."""
        self.calls.append(node)
        return list(self.table.get(node, []))


def build(table, root="A"):
    """Построить граф по словарю и вернуть его вместе с источником."""
    source = DictSource(table)
    return build_graph(source, root), source


class GraphTests(unittest.TestCase):
    """Проверки BFS и работы с циклами."""

    def test_bfs_order(self):
        """Узлы раскрываются по уровням, каждый один раз."""
        graph, source = build({"A": ["B", "C"], "B": ["D"], "C": ["D"]})
        self.assertEqual(list(graph.edges), ["A", "B", "C", "D"])
        self.assertEqual(sorted(source.calls), ["A", "B", "C", "D"])
        self.assertEqual(graph.edge_count(), 4)

    def test_progress_callback(self):
        """Обработчик прогресса вызывается для каждого уровня."""
        seen = []
        source = DictSource({"A": ["B"], "B": ["C"]})
        build_graph(source, "A", lambda level, done: seen.append((level, done)))
        self.assertEqual(seen, [(["A"], 0), (["B"], 1), (["C"], 2)])

    def test_single_node(self):
        """Пакет без зависимостей даёт граф из одного узла."""
        graph, _ = build({})
        self.assertEqual(graph.edges, {"A": []})
        self.assertEqual(find_cycles(graph), [])

    def test_cycle(self):
        """Цикл не приводит к бесконечному обходу и находится."""
        graph, source = build({"A": ["B"], "B": ["C"], "C": ["A"]})
        self.assertEqual(len(source.calls), 3)
        self.assertEqual(find_cycles(graph), [["A", "B", "C", "A"]])

    def test_self_cycle(self):
        """Зависимость от самого себя считается циклом."""
        graph, _ = build({"A": ["A"]})
        self.assertEqual(find_cycles(graph), [["A", "A"]])

    def test_two_cycles(self):
        """Независимые циклы находятся оба."""
        table = {"A": ["B", "C"], "B": ["A"], "C": ["D"], "D": ["C"]}
        graph, _ = build(table)
        self.assertEqual(
            find_cycles(graph), [["A", "B", "A"], ["C", "D", "C"]]
        )

    def test_no_false_cycle_in_diamond(self):
        """Ромб без обратных рёбер не считается циклом."""
        graph, _ = build({"A": ["B", "C"], "B": ["D"], "C": ["D"]})
        self.assertEqual(find_cycles(graph), [])

    def test_deep_chain(self):
        """Рекурсия справляется с цепочкой в несколько сотен узлов."""
        size = 300
        table = {str(i): [str(i + 1)] for i in range(size)}
        graph, _ = build(table, root="0")
        self.assertEqual(len(graph.edges), size + 1)


class TreeTests(unittest.TestCase):
    """Проверки построчного описания дерева."""

    def test_diamond(self):
        """Повторный узел с поддеревом помечается как повтор."""
        graph, _ = build(
            {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["E"]}
        )
        lines = [(x.prefix, x.node, x.mark) for x in tree_lines(graph)]
        self.assertEqual(
            lines,
            [
                ("|-- ", "B", None),
                ("|   `-- ", "D", None),
                ("|       `-- ", "E", None),
                ("`-- ", "C", None),
                ("    `-- ", "D", MARK_SEEN),
            ],
        )

    def test_repeated_leaf_not_marked(self):
        """Повторный лист выводится без пометки."""
        graph, _ = build({"A": ["B", "C"], "B": ["D"], "C": ["D"]})
        marks = [line.mark for line in tree_lines(graph)]
        self.assertEqual(marks, [None, None, None, None])

    def test_cycle_mark(self):
        """Ребро назад по пути помечается как цикл и не раскрывается."""
        graph, _ = build({"A": ["B"], "B": ["A"]})
        lines = tree_lines(graph)
        self.assertEqual([x.node for x in lines], ["B", "A"])
        self.assertEqual(lines[-1].mark, MARK_CYCLE)


if __name__ == "__main__":
    unittest.main()
