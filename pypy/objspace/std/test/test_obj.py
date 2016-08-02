from __future__ import with_statement
from pypy.conftest import option

class AppTestObject:

    spaceconfig = {'usemodules': ['itertools']}

    def setup_class(cls):
        from pypy.interpreter import gateway
        import sys

        space = cls.space
        cls.w_cpython_behavior = space.wrap(not option.runappdirect)
        cls.w_cpython_version = space.wrap(tuple(sys.version_info))
        cls.w_appdirect = space.wrap(option.runappdirect)
        cls.w_cpython_apptest = space.wrap(option.runappdirect and not hasattr(sys, 'pypy_translation_info'))

        def w_unwrap_wrap_unicode(space, w_obj):
            return space.wrap(space.unicode_w(w_obj))
        cls.w_unwrap_wrap_unicode = space.wrap(gateway.interp2app(w_unwrap_wrap_unicode))
        def w_unwrap_wrap_bytes(space, w_obj):
            return space.newbytes(space.bytes_w(w_obj))
        cls.w_unwrap_wrap_bytes = space.wrap(gateway.interp2app(w_unwrap_wrap_bytes))

    def test_hash_builtin(self):
        if not self.cpython_behavior:
            skip("on pypy-c id == hash is not guaranteed")
        if self.cpython_version >= (2, 7):
            skip("on CPython >= 2.7, id != hash")
        import sys
        o = object()
        assert (hash(o) & sys.maxsize) == (id(o) & sys.maxsize)

    def test_hash_method(self):
        o = object()
        assert hash(o) == o.__hash__()

    def test_hash_list(self):
        l = list(range(5))
        raises(TypeError, hash, l)

    def test_no_getnewargs(self):
        o = object()
        assert not hasattr(o, '__getnewargs__')

    def test_hash_subclass(self):
        import sys
        class X(object):
            pass
        x = X()
        if self.cpython_behavior and self.cpython_version < (2, 7):
            assert (hash(x) & sys.maxsize) == (id(x) & sys.maxsize)
        assert hash(x) == object.__hash__(x)

    def test_reduce_recursion_bug(self):
        class X(object):
            def __reduce__(self):
                return object.__reduce__(self) + (':-)',)
        s = X().__reduce__()
        assert s[-1] == ':-)'

    def test_default_format(self):
        class x(object):
            def __str__(self):
                return "Pickle"
        res = format(x())
        assert res == "Pickle"
        assert isinstance(res, str)

    def test_subclasshook(self):
        class x(object):
            pass
        assert x().__subclasshook__(object()) is NotImplemented
        assert x.__subclasshook__(object()) is NotImplemented

    def test_object_init(self):
        import warnings

        class A(object):
            pass

        raises(TypeError, A().__init__, 3)
        raises(TypeError, A().__init__, a=3)

        class B(object):
            def __new__(cls):
                return super(B, cls).__new__(cls)

            def __init__(self):
                super(B, self).__init__(a=3)

        #-- pypy doesn't raise the DeprecationWarning
        #with warnings.catch_warnings(record=True) as log:
        #    warnings.simplefilter("always", DeprecationWarning)
        #    B()
        #assert len(log) == 1
        #assert log[0].message.args == ("object.__init__() takes no parameters",)
        #assert type(log[0].message) is DeprecationWarning

    def test_object_str(self):
        # obscure case: __str__() must delegate to __repr__() without adding
        # type checking on its own
        class A(object):
            def __repr__(self):
                return 123456
        assert A().__str__() == 123456

    def test_object_dir(self):
        class A(object):
            a_var = None

        assert hasattr(object, '__dir__')
        obj = A()
        obj_items = dir(obj)
        assert obj_items == sorted(obj_items)
        assert obj_items == sorted(object.__dir__(obj))


    def test_is_on_primitives(self):
        if self.cpython_apptest:
            skip("cpython behaves differently")
        assert 1 is 1
        x = 1000000
        assert x + 1 is int(str(x + 1))
        assert 1 is not 1.0
        assert 1.1 is 1.1
        assert 0.0 is not -0.0
        for x in range(10):
            assert x + 0.1 is x + 0.1
        for x in range(10):
            assert x + 1 is x + 1
        for x in range(10):
            assert x+1j is x+1j
            assert 1+x*1j is 1+x*1j
        l = [1]
        assert l[0] is l[0]

    def test_is_on_strs(self):
        if self.appdirect:
            skip("cannot run this test as apptest")
        l = ["a"]
        assert l[0] is l[0]
        u = "a"
        assert self.unwrap_wrap_unicode(u) is u
        s = b"a"
        assert self.unwrap_wrap_bytes(s) is s

    def test_is_on_subclasses(self):
        for typ in [int, float, complex, str]:
            class mytyp(typ):
                pass
            if not self.cpython_apptest and typ is not str:
                assert typ(42) is typ(42)
            assert mytyp(42) is not mytyp(42)
            assert mytyp(42) is not typ(42)
            assert typ(42) is not mytyp(42)
            x = mytyp(42)
            assert x is x
            assert x is not "43"
            assert x is not None
            assert "43" is not x
            assert None is not x
            x = typ(42)
            assert x is x
            assert x is not "43"
            assert x is not None
            assert "43" is not x
            assert None is not x

    def test_id_on_primitives(self):
        if self.cpython_apptest:
            skip("cpython behaves differently")
        assert id(1) == (1 << 4) + 1
        class myint(int):
            pass
        assert id(myint(1)) != id(1)

        assert id(1.0) & 7 == 5
        assert id(-0.0) != id(0.0)
        assert hex(id(2.0)) == '0x40000000000000005'
        assert id(0.0) == 5

    def test_id_on_strs(self):
        if self.appdirect:
            skip("cannot run this test as apptest")
        for u in [u"", u"a", u"aa"]:
            assert id(self.unwrap_wrap_unicode(u)) == id(u)
            s = u.encode()
            assert id(self.unwrap_wrap_bytes(s)) == id(s)
        #
        assert id(b'') == (256 << 4) | 11     # always
        assert id(u'') == (257 << 4) | 11
        assert id(b'a') == (ord('a') << 4) | 11
        assert id(u'\u1234') == ((~0x1234) << 4) | 11

    def test_id_of_tuples(self):
        l = []
        x = (l,)
        assert id(x) != id((l,))          # no caching at all
        if self.appdirect:
            skip("cannot run this test as apptest")
        assert id(()) == (258 << 4) | 11     # always

    def test_id_of_frozensets(self):
        x = frozenset([4])
        assert id(x) != id(frozenset([4]))          # no caching at all
        if self.appdirect:
            skip("cannot run this test as apptest")
        assert id(frozenset()) == (259 << 4) | 11     # always
        assert id(frozenset([])) == (259 << 4) | 11   # always

    def test_identity_vs_id_primitives(self):
        import sys
        l = list(range(-10, 10, 2))
        for i in [0, 1, 3]:
            l.append(float(i))
            l.append(i + 0.1)
            l.append(i + sys.maxsize)
            l.append(i - sys.maxsize)
            l.append(i + 1j)
            l.append(i - 1j)
            l.append(1 + i * 1j)
            l.append(1 - i * 1j)
            l.append((i,))
            l.append(frozenset([i]))
        l.append(-0.0)
        l.append(None)
        l.append(True)
        l.append(False)
        l.append(())
        l.append(tuple([]))
        l.append(frozenset())

        for i, a in enumerate(l):
            for b in l[i:]:
                assert (a is b) == (id(a) == id(b))
                if a is b:
                    assert a == b

    def test_identity_vs_id_str(self):
        if self.appdirect:
            skip("cannot run this test as apptest")
        l = []
        def add(s, u):
            l.append(s)
            l.append(self.unwrap_wrap_bytes(s))
            l.append(s[:1] + s[1:])
            l.append(u)
            l.append(self.unwrap_wrap_unicode(u))
            l.append(u[:1] + u[1:])
        for i in range(3, 18):
            add(str(i).encode(), str(i))
        add(b"s", u"s")
        add(b"", u"")

        for i, a in enumerate(l):
            for b in l[i:]:
                assert (a is b) == (id(a) == id(b))
                if a is b:
                    assert a == b

    def test_identity_bug(self):
        x = 0x4000000000000000
        y = 2j
        assert id(x) != id(y)

    def test_object_hash_immutable(self):
        x = 42
        y = 40
        y += 2
        assert object.__hash__(x) == object.__hash__(y)

    def test_richcompare(self):
        o = object()
        o2 = object()
        assert o.__eq__(o) is True
        assert o.__eq__(o2) is NotImplemented
        assert o.__ne__(o) is False
        assert o.__ne__(o2) is True
        assert o.__le__(o2) is NotImplemented
        assert o.__lt__(o2) is NotImplemented
        assert o.__ge__(o2) is NotImplemented
        assert o.__gt__(o2) is NotImplemented

def test_isinstance_shortcut():
    from pypy.objspace.std import objspace
    space = objspace.StdObjSpace()
    w_a = space.wrap("a")
    space.type = None
    # if it crashes, it means that space._type_isinstance didn't go through
    # the fast path, and tries to call type() (which is set to None just
    # above)
    space.isinstance_w(w_a, space.w_unicode) # does not crash
