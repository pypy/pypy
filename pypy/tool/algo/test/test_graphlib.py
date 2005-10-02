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
