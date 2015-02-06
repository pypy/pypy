

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

    def test_len(self):
        import pypystm
        h = pypystm.hashtable()
        assert len(h) == 0
        h[42] = "foo"
        assert len(h) == 1
        h[43] = "bar"
        assert len(h) == 2
        h[42] = "baz"
        assert len(h) == 2
        del h[42]
        assert len(h) == 1

    def test_keys_values_items(self):
        import pypystm
        h = pypystm.hashtable()
        h[42] = "foo"
        h[43] = "bar"
        assert sorted(h.keys()) == [42, 43]
        assert sorted(h.values()) == ["bar", "foo"]
        assert sorted(h.items()) == [(42, "foo"), (43, "bar")]
