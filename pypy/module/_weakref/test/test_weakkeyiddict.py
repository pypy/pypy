class AppTestWeakKeyIdDict(object):
    spaceconfig = dict(usemodules=('_weakref',))

    def test_simple(self):
        import _weakref
        class A(object):
            pass
        d = _weakref.weakkeyiddict()
        a1 = A()
        a2 = A()
        d[a1] = 11
        d[a2] = 22.5
        assert d[a1] == 11
        assert d[a2] == 22.5
        assert d.get(a2, 5) == 22.5
        del d[a2]
        raises(KeyError, "d[a2]")
        assert d.get(a2, 5) == 5
        assert a1 in d
        assert a2 not in d
        assert d.setdefault(a1, 82) == 11
        assert d[a1] == 11
        assert d.setdefault(a2, 83) == 83
        assert d[a2] == 83

    def test_nonhashable_key(self):
        import _weakref
        d = _weakref.weakkeyiddict()
        lst = []
        lst2 = []
        d[lst] = 84
        assert lst in d
        assert lst2 not in d
        assert d.pop(lst) == 84
        assert lst not in d
        assert d.pop(lst, 85) == 85

    def test_collect(self):
        import _weakref
        gone = []
        class A(object):
            def __del__(self):
                gone.append(True)
        d = _weakref.weakkeyiddict()
        a1 = A()
        a2 = A()
        d[a1] = -42
        d[a2] = 83
        assert gone == []
        #
        del a1
        tries = 0
        while not gone:
            tries += 1
            if tries > 5:
                raise AssertionError("a1 doesn't disappear")
            gc.collect()
        assert gone == [True]
        assert d[a2] == 83
