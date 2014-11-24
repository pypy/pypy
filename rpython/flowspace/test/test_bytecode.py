"""Unit tests for rpython.flowspace.bytecode"""

from rpython.flowspace.bytecode import bc_reader

def test_graph_dump():
    def f(x):
        if x:
            return 1
        else:
            return 0
    bc_graph = bc_reader.build_flow(bc_reader.build_code(f.__code__))
    print bc_graph.dump()
    assert [lst[0].offset for lst in bc_graph.dump()] == [0, 6, 10]
