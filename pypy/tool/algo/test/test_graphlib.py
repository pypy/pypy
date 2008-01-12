import autopath
import random
from pypy.tool.algo.graphlib import *

def copy_edges(edges):
    result = {}
    for key, value in edges.items():
        result[key] = value[:]
    return result

# ____________________________________________________________

class TestSimple:
    edges = {
        'A': [Edge('A','B'), Edge('A','C')],
        'B': [Edge('B','D'), Edge('B','E')],
        'C': [Edge('C','F')],
        'D': [Edge('D','D')],
        'E': [Edge('E','A'), Edge('E','C')],
        'F': [],
        'G': [],
        }

    def test_strong_components(self):
        edges = self.edges
        saved = copy_edges(edges)
        result = list(strong_components(edges, edges))
        assert edges == saved
        for comp in result:
            comp = list(comp)
            comp.sort()
        result = [''.join(comp) for comp in result]
        result.sort()
        assert result == ['ABE', 'C', 'D', 'F', 'G']

    def test_all_cycles(self):
        edges = self.edges
        saved = copy_edges(edges)
        cycles = list(all_cycles('A', edges, edges))
        assert edges == saved
        cycles.sort()
        expected = [
            [edges['A'][0], edges['B'][1], edges['E'][0]],
            [edges['D'][0]],
            ]
        expected.sort()
        assert cycles == expected

    def test_break_cycles(self):
        edges = self.edges
        saved = copy_edges(edges)
        result = list(break_cycles(edges, edges))
        assert edges == saved
        assert len(result) == 2
        assert edges['D'][0] in result
        assert (edges['A'][0] in result or
                edges['B'][1] in result or
                edges['E'][0] in result)


class TestLoops:
    # a graph with 20 loops of length 10 each, plus an edge from each loop to
    # the next, non-cylically
    edges = {}
    for i in range(200):
        j = i+1
        if j % 10 == 0:
            j -= 10
        edges[i] = [Edge(i, j)]
    for i in range(19):
        edges[i*10].append(Edge(i*10, i*10+15))
    vertices = dict([(i, True) for i in range(200)])

    def test_strong_components(self):
        edges = self.edges
        result = list(strong_components(self.vertices, edges))
        assert len(result) == 20
        result.sort()
        for i in range(20):
            comp = list(result[i])
            comp.sort()
            assert comp == range(i*10, (i+1)*10)

    def test_break_cycles(self, edges=None):
        edges = edges or self.edges
        result = list(break_cycles(self.vertices, edges))
        assert len(result) == 20
        result = [(edge.source, edge.target) for edge in result]
        result.sort()
        for i in range(20):
            assert i*10 <= result[i][0] <= (i+1)*10
            assert i*10 <= result[i][1] <= (i+1)*10

    def test_break_cycles_2(self):
        edges = copy_edges(self.edges)
        edges[190].append(Edge(190, 5))
        self.test_break_cycles(edges)


class TestTree:
    edges = make_edge_dict([Edge(i//2, i) for i in range(1, 52)])

    def test_strong_components(self):
        result = list(strong_components(self.edges, self.edges))
        assert len(result) == 52
        vertices = []
        for comp in result:
            assert len(comp) == 1
            vertices += comp
        vertices.sort()
        assert vertices == range(52)

    def test_all_cycles(self):
        result = list(all_cycles(0, self.edges, self.edges))
        assert not result

    def test_break_cycles(self):
        result = list(break_cycles(self.edges, self.edges))
        assert not result


class TestChainAndLoop:
    edges = make_edge_dict([Edge(i,i+1) for i in range(100)] + [Edge(100,99)])

    def test_strong_components(self):
        result = list(strong_components(self.edges, self.edges))
        assert len(result) == 100
        vertices = []
        for comp in result:
            assert (len(comp) == 1 or
                    (len(comp) == 2 and 99 in comp and 100 in comp))
            vertices += comp
        vertices.sort()
        assert vertices == range(101)


class TestBugCase:
    edges = make_edge_dict([Edge(0,0), Edge(1,0), Edge(1,2), Edge(2,1)])

    def test_strong_components(self):
        result = list(strong_components(self.edges, self.edges))
        assert len(result) == 2
        result.sort()
        assert list(result[0]) == [0]
        assert list(result[1]) in ([1,2], [2,1])


class TestRandom:
    edges = make_edge_dict([Edge(random.randrange(0,100),
                                 random.randrange(0,100)) for i in range(150)])

    def test_strong_components(self):
        result = list(strong_components(self.edges, self.edges))
        vertices = []
        for comp in result:
            vertices += comp
        vertices.sort()
        expected = self.edges.keys()
        expected.sort()
        assert vertices == expected
