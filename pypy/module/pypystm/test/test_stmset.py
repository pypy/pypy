

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

    def test_list_from_set(self):
        import pypystm
        s = pypystm.stmset()
        assert len(s) == 0
        assert tuple(s) == ()
        s.add(42.5)
        s.add(42.0)
        assert sorted(s) == [42.0, 42.5]
        assert len(s) == 2
        s.remove(42.0)
        assert list(s) == [42.5]
        #
        class Key(object):
            def __hash__(self):
                return hash(42.5)
        key3 = Key()
        s.add(key3)
        assert len(s) == 2
        items = list(s)
        assert items == [42.5, key3] or items == [key3, 42.5]

    def test_iterator(self):
        import pypystm
        class A(object):
            def __hash__(self):
                return 42
        class B(object):
            pass
        d = pypystm.stmset()
        a1 = A()
        a2 = A()
        b0 = B()
        d.add(a1)
        d.add(a2)
        d.add(b0)
        assert sorted(d) == sorted([a1, a2, b0])
