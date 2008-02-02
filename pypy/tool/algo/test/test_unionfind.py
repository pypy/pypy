from pypy.tool.algo.unionfind import UnionFind


def test_cleanup():
    state = []
    class ReferencedByExternalState(object):
        def __init__(self, obj):
            state.append(self)
            self.obj = obj

        def update(self, other):
            pass

        def cleanup(self):
            state.remove(self)

    uf = UnionFind(ReferencedByExternalState)
    uf.find(1)
    for i in xrange(1, 10, 2):
        uf.union(i, 1)
    uf.find(2)
    for i in xrange(2, 20, 2):
        uf.union(i, 2)
    assert len(state) < 3


