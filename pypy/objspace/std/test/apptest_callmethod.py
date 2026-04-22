# The exec hacking is needed to have the code snippets compiled
# by our own compiler, not CPython's

def test_call_method():
    exec("""if 1:
        class C(object):
            def m(*args, **kwds):
                return args, kwds
            sm = staticmethod(m)
            cm = classmethod(m)

        c = C()
        assert c.m() == ((c,), {})
        assert c.sm() == ((), {})
        assert c.cm() == ((C,), {})
        assert c.m(5) == ((c, 5), {})
        assert c.sm(6) == ((6,), {})
        assert c.cm(7) == ((C, 7), {})
        assert c.m(5, x=3) == ((c, 5), {'x': 3})
        assert c.m(*range(5)) == ((c, 0, 1, 2, 3, 4), {})
        assert c.m(**{'u': 4}) == ((c,), {'u': 4})
    """)

def test_call_attribute():
    exec("""if 1:
        class C(object):
            def m(*args, **kwds):
                return args, kwds
        def myfunc(*args):
            return args

        c = C()
        c.m = c.m2 = myfunc
        assert c.m() == ()
        assert c.m(5, 2) == (5, 2)
        assert c.m2(4) == (4,)
        assert c.m2("h", "e", "l", "l", "o") == tuple("hello")
    """)

def test_call_module():
    exec("""if 1:
        import sys
        try:
            sys.exit(5)
        except SystemExit as e:
            assert e.args == (5,)
        else:
            raise Exception("did not raise?")
    """)

def test_custom_getattr():
    exec("""if 1:
        class C(object):
            def __getattr__(self, name):
                if name == 'bla':
                    return myfunc
                raise AttributeError
        def myfunc(*args):
            return args

        c = C()
        assert c.bla(1, 2, 3) == (1, 2, 3)
    """, {})

def test_custom_getattribute():
    exec("""if 1:
        class C(object):
            def __getattribute__(self, name):
                if name == 'bla':
                    return myfunc
                raise AttributeError
            def bla(self):
                Boom
        def myfunc(*args):
            return args

        c = C()
        assert c.bla(1, 2, 3) == (1, 2, 3)
    """, {})

def test_builtin():
    exec("""if 1:
        class C(object):
            foobar = len
        c = C()
        assert c.foobar("hello") == 5
    """)

def test_builtin_no_self_prepend():
    # builtin_function (e.g. len/repr) must NOT use the fast method path.
    # If it did, LOAD_METHOD would push (len, c) and CALL_METHOD would call
    # len(c, "hello") instead of len("hello"), causing a TypeError.
    exec("""if 1:
        class C(object):
            describe = repr
            count = len
        c = C()
        assert c.describe("x") == repr("x")
        assert c.count("hello") == 5
    """)

def test_method_descriptor_direct_call_contract():
    # For any type used via the fast method path (flag_method_descriptor=True),
    # calling descriptor(self, *args) must equal descriptor.__get__(self, T)(*args).
    # Verifies the behavioral contract the LOAD_METHOD optimization relies on.
    exec("""if 1:
        class C(object):
            def f(self, x):
                return (self, x)
            def g(self, x, y=0):
                return (self, x, y)

        c = C()
        # fast path calls C.f(c, 1) directly; bound method calls c.f(1)
        assert C.f(c, 1) == c.f(1)
        assert C.g(c, 2, y=3) == c.g(2, y=3)

        # staticmethod: __get__ strips self, direct call must NOT prepend self
        class D(object):
            sm = staticmethod(lambda x: x * 2)
        d = D()
        assert d.sm(4) == 8

        # classmethod: __get__ prepends the class, not the instance
        class E(object):
            cm = classmethod(lambda cls, x: (cls, x))
        e = E()
        assert e.cm(5) == (E, 5)
    """)

def test_attributeerror():
    exec("""if 1:
        assert 5 .__add__(6) == 11
        try:
            6 .foobar(7)
        except AttributeError:
            pass
        else:
            raise Exception("did not raise?")
    """)

def test_kwargs():
    exec("""if 1:
        class C(object):
            def f(self, a):
                return a + 2
        
        assert C().f(a=3) == 5
    """)
