

class AppTestDict:
    spaceconfig = dict(usemodules=['pypystm'])

    def test_simple(self):
        import pypystm
        d = pypystm.stmdict()
        raises(KeyError, "d[42.0]")
        d[42.0] = "5"
        assert d[42.0] == "5"
        assert 42.0 in d
        assert d.get(42.0) == "5"
        assert d.get(42.0, 42) == "5"
        del d[42.0]
        raises(KeyError, "d[42.0]")
        assert 42.0 not in d
        assert d.get(42.0) is None
        assert d.get(42.0, "41") == "41"
        assert d.setdefault(42.0, "42") == "42"
        assert d.setdefault(42.0, "43") == "42"
        assert d.setdefault(42.5) is None
        assert d[42.5] is None
        assert d[42.0] == "42"
        d[42.0] = "foo"
        assert d[42.0] == "foo"

    def test_hash_collision(self):
        import pypystm
        key1 = 5L
        key2 = 5L + 2**64 - 1
        key3 = 5L + 2**65 - 2
        assert hash(key1) == hash(key2) == hash(key3)
        d = pypystm.stmdict()
        d[key1] = 1.0
        d[key2] = 2.0
        assert d[key1] == 1.0
        assert key2 in d
        assert key3 not in d
        raises(KeyError, "d[key3]")
        assert d.get(key3) is None
        del d[key1]
        assert key1 not in d
        assert d[key2] == 2.0
        assert key3 not in d
        raises(KeyError, "del d[key1]")
        del d[key2]
        assert key1 not in d
        assert key2 not in d
        assert key3 not in d
        raises(KeyError, "del d[key3]")
        assert d.setdefault(key1, 5.0) == 5.0
        assert d.setdefault(key2, 7.5) == 7.5
        assert d.setdefault(key1, 2.3) == 5.0

    def test_must_be_hashable(self):
        import pypystm
        d = pypystm.stmdict()
        raises(TypeError, "d[[]]")
        raises(TypeError, "d[[]] = 5")
        raises(TypeError, "del d[[]]")
        raises(TypeError, "[] in d")
        raises(TypeError, "d.get([])")
        raises(TypeError, "d.setdefault([], 0)")

    def test_equal_elements(self):
        import pypystm
        d = pypystm.stmdict()
        d[42.0] = "hello"
        assert d[42] == "hello"
        assert d.get(42L) == "hello"
        assert d.get(42.001) is None
