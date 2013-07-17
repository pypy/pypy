

class AppTestIntOp:
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_int_add(self):
        import sys
        from __pypy__ import intop
        assert intop.int_add(40, 2) == 42
        assert intop.int_add(sys.maxint, 1) == -sys.maxint-1
        assert intop.int_add(-2, -sys.maxint) == sys.maxint
