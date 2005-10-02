import autopath
from pypy.tool.algo.graphlib import *

edges = {
    'A': [Edge('A','B'), Edge('A','C')],
    'B': [Edge('B','D'), Edge('B','E')],
    'C': [Edge('C','F')],
    'D': [Edge('D','D')],
    'E': [Edge('E','A'), Edge('E','C')],
    'F': [],
    'G': [],
    }

def copy_edges(edges):
    result = {}
    for key, value in edges.items():
        result[key] = value[:]
    return result


def test_strong_components():
    saved = copy_edges(edges)
    result = list(strong_components(edges, edges))
    assert edges == saved
    for comp in result:
        comp = list(comp)
        comp.sort()
    result = [''.join(comp) for comp in result]
    result.sort()
    assert result == ['ABE', 'C', 'D', 'F', 'G']

def test_all_cycles():
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

def test_break_cycles():
    saved = copy_edges(edges)
    result = list(break_cycles(edges, edges))
    assert edges == saved
    assert len(result) == 2
    assert edges['D'][0] in result
    assert (edges['A'][0] in result or
            edges['B'][1] in result or
            edges['E'][0] in result)

def test_break_cycles_2():
    # a graph with 20 loops of length 10 each, plus an edge from each loop to
    # the next
    edges = {}
    for i in range(200):
        j = i+1
        if j % 10 == 0:
            j -= 10
        edges[i] = [Edge(i, j)]
    for i in range(20):
        edges[i*10].append(Edge(i*10, (i*10+15) % 200))
    #
    result = list(break_cycles(edges, edges))
    assert len(result) == 20
    result = [(edge.source, edge.target) for edge in result]
    result.sort()
    for i in range(20):
        assert i*10 <= result[i][0] <= (i+1)*10
        assert i*10 <= result[i][1] <= (i+1)*10
