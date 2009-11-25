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

    def test_break_cycles_v(self):
        edges = copy_edges(self.edges)
        edges['R'] = [Edge('R', 'B')]
        saved = copy_edges(edges)
        result = list(break_cycles_v(edges, edges))
        assert edges == saved
        assert len(result) == 2
        result.sort()
        assert ''.join(result) == 'AD'
        # the answers 'BD' and 'DE' are correct too, but 'AD' should
        # be picked because 'A' is the cycle's node that is the further
        # from the root 'R'.

    def test_find_roots(self):
        roots = list(find_roots(self.edges, self.edges))
        roots.sort()
        assert ''.join(roots) in ('AG', 'BG', 'EG')

        edges = copy_edges(self.edges)
        edges['R'] = [Edge('R', 'B')]
        roots = list(find_roots(edges, edges))
        roots.sort()
        assert ''.join(roots) == 'GR'


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
        result2 = []
        for comp in result:
            comp = list(comp)
            comp.sort()
            result2.append(comp)
        result2.sort()
        for i in range(20):
            comp = result2[i]
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

    def test_find_roots(self):
        roots = find_roots(self.vertices, self.edges)
        assert len(roots) == 1
        v = list(roots)[0]
        assert v in range(10)

    def test_find_roots_2(self):
        edges = copy_edges(self.edges)
        edges[190].append(Edge(190, 5))
        roots = find_roots(self.vertices, edges)
        assert len(roots) == 1


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

    def test_find_roots(self):
        roots = find_roots(self.edges, self.edges)
        assert len(roots) == 1
        v = list(roots)[0]
        assert v == 0


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

class TestBadCase:
    # a complete graph
    NUM = 50
    edges = make_edge_dict([Edge(i, j) for i in range(NUM)
                                       for j in range(NUM)])
    vertices = dict.fromkeys(range(NUM))

    def test_break_cycles(self):
        result = list(break_cycles(self.edges, self.edges))
        print len(result)
        assert result

    def test_find_roots(self):
        roots = find_roots(self.edges, self.edges)
        assert len(roots) == 1
        assert list(roots)[0] in self.edges


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

    def test_break_cycles(self):
        list(break_cycles(self.edges, self.edges))
        # assert is_acyclic(): included in break_cycles() itself

    def test_break_cycles_v(self):
        result = list(break_cycles_v(self.edges, self.edges))
        # assert is_acyclic(): included in break_cycles_v() itself
        print len(result), 'vertices removed'

    def test_find_roots(self):
        roots = find_roots(self.edges, self.edges)
        reachable = set()
        for root in roots:
            reachable |= set(vertices_reachable_from(root, self.edges,
                                                     self.edges))
        assert reachable == set(self.edges)
