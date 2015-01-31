

class AppTestSet:
    spaceconfig = dict(usemodules=['pypystm'])

    def test_simple(self):
        import pypystm
        s = pypystm.stmset()
        s.add(42.0)
        assert 42.0 in s
        assert 42.5 not in s
        s.add(42.5)
        assert 42.0 in s
        assert 42.5 in s
        s.add(42.5)
        assert 42.0 in s
        assert 42.5 in s
        s.remove(42.0)
        assert 42.0 not in s
        assert 42.5 in s
        raises(KeyError, s.remove, 42.0)
        s.discard(42.0)
        assert 42.0 not in s
        assert 42.5 in s
        s.discard(42.5)
        assert 42.5 not in s

    def test_hash_collision(self):
        import pypystm
        class Key(object):
            def __hash__(self):
                return 42
        key1 = Key()
        key2 = Key()
        key3 = Key()
        s = pypystm.stmset()
        s.add(key1)
        s.add(key2)
        assert key1 in s
        assert key2 in s
        assert key3 not in s
        s.remove(key1)
        assert key1 not in s
        assert key2 in s
        assert key3 not in s
        s.remove(key2)
        assert key1 not in s
        assert key2 not in s
        assert key3 not in s

    def test_must_be_hashable(self):
        import pypystm
        s = pypystm.stmset()
        raises(TypeError, s.add, [])
        raises(TypeError, s.remove, [])
        raises(TypeError, s.discard, [])

    def test_equal_elements(self):
        import pypystm
        s = pypystm.stmset()
        s.add(42.0)
        assert 42 in s
        assert 42L in s
        assert 42.001 not in s
