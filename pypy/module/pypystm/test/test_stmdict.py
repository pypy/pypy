

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

    def test_list_from_dict(self):
        import pypystm
        d = pypystm.stmdict()
        assert len(d) == 0
        assert tuple(d) == ()
        d[42.5] = "foo"
        d[42.0] = ["bar"]
        assert sorted(d) == [42.0, 42.5]
        assert len(d) == 2
        del d[42]
        assert len(d) == 1
        assert list(d) == [42.5]
        #
        class Key(object):
            def __hash__(self):
                return hash(42.5)
        key3 = Key()
        d[key3] = "other"
        assert len(d) == 2
        items = list(d)
        assert items == [42.5, key3] or items == [key3, 42.5]

    def test_keys_values_items(self):
        import pypystm
        d = pypystm.stmdict()
        d[42.5] = "bar"
        d[42.0] = "foo"
        assert sorted(d.keys()) == [42.0, 42.5]
        assert sorted(d.values()) == ["bar", "foo"]
        assert sorted(d.items()) == [(42.0, "foo"), (42.5, "bar")]

    def test_pop(self):
        import pypystm
        d = pypystm.stmdict()
        raises(KeyError, d.pop, 42.0)
        assert d.pop(42.0, "foo") == "foo"
        raises(KeyError, "d[42.0]")
        d[42.0] = "bar"
        res = d.pop(42.0)
        assert res == "bar"
        raises(KeyError, "d[42.0]")
        d[42.0] = "bar"
        res = d.pop(42.0, "foo")
        assert res == "bar"
        raises(KeyError, "d[42.0]")

    def test_popitem(self):
        import pypystm
        d = pypystm.stmdict()
        raises(KeyError, d.popitem)
        d[42.0] = "bar"
        assert len(d) == 1
        res = d.popitem()
        assert res == (42.0, "bar")
        raises(KeyError, d.popitem)
        raises(KeyError, "d[42.0]")
        assert len(d) == 0


    def test_custom_evil_eq(self):
        class A(object):
            depth = []
            def __hash__(self):
                return 1
            def __eq__(self, other):
                if not self.depth:
                    self.depth.append(1)
                    del d[a]
                    print "del a"
                return self is other
        import pypystm
        d = pypystm.stmdict()
        a = A()
        b = A()
        d[a] = "a"
        d[b] = "b" # dels a
        assert a not in d
        assert b in d

    def test_custom_evil_eq2(self):
        class A(object):
            depth = []
            def __hash__(self):
                return 1
            def __eq__(self, other):
                if not self.depth:
                    self.depth.append(1)
                    del d[a]
                    print "del a"
                return self is other
        import pypystm
        d = pypystm.stmdict()
        a = A()
        b = A()
        d[a] = "a"
        assert d.get(b) is None
        assert a not in d
        assert b not in d
        assert d.keys() == []


    def test_iterator(self):
        import pypystm
        class A(object):
            def __hash__(self):
                return 42
        class B(object):
            pass
        d = pypystm.stmdict()
        a1 = A()
        a2 = A()
        b0 = B()
        d[a1] = "foo"
        d[a2] = None
        d[b0] = "bar"
        assert sorted(d) == sorted([a1, a2, b0])
        assert sorted(d.iterkeys()) == sorted([a1, a2, b0])
        assert sorted(d.itervalues()) == [None, "bar", "foo"]
        assert sorted(d.iteritems()) == sorted([(a1, "foo"), (a2, None),
                                                (b0, "bar")])
