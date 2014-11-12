

class AppTestHashtable:
    spaceconfig = dict(usemodules=['_stm'])

    def test_simple(self):
        import _stm
        t1 = _stm.time()
        t2 = _stm.time()
        assert t1 < t2 < t1 + 1
        t1 = _stm.clock()
        t2 = _stm.clock()
        assert t1 < t2 < t1 + 1
