

class AppTestHashtable:
    spaceconfig = dict(usemodules=['pypystm'])

    def test_simple(self):
        import pypystm
        h = pypystm.hashtable()
        h[42+65536] = "bar"
        raises(KeyError, "h[42]")
        h[42] = "foo"
        assert h[42] == "foo"
        assert 42 in h
        del h[42]
        assert 42 not in h
        raises(KeyError, "h[42]")
        assert h[42+65536] == "bar"
        raises(KeyError, "del h[42]")

    def test_get_setdefault(self):
        import pypystm
        h = pypystm.hashtable()
        assert h.get(42) is None
        assert h.get(-43, None) is None
        assert h.get(44, 81) == 81
        raises(KeyError, "h[42]")
        raises(KeyError, "h[-43]")
        raises(KeyError, "h[44]")
        assert h.setdefault(42) is None
        assert h[42] is None
        assert h.setdefault(42, "81") is None
        assert h[42] is None
        assert h.setdefault(44, "-81") == "-81"
        assert h[44] == "-81"
        assert h[42] is None
