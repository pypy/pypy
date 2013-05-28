class AppTestUnroller(object):
    spaceconfig = {"usemodules": ["__pypy__"]}

    def test_iter(self):
        from __pypy__ import unroll_loop

        res = []
        for i in unroll_loop(xrange(3)):
            res.append(i)
        assert res == [0, 1, 2]

    def test_repr(self):
        from __pypy__ import unroll_loop

        assert repr(unroll_loop([1, 2, 3])) == "LoopUnroller(%r)" % [1, 2, 3]
