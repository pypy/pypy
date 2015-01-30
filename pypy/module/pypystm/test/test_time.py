

class AppTestHashtable:
    spaceconfig = dict(usemodules=['pypystm'])

    def test_simple(self):
        import pypystm
        t1 = pypystm.time()
        t2 = pypystm.time()
        assert t1 < t2 < t1 + 1
        t1 = pypystm.clock()
        t2 = pypystm.clock()
        assert t1 < t2 < t1 + 1
