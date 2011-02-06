from pypy.tool.udir import udir


class AppTestMarshal:
    def setup_class(cls):
        tmpfile = udir.join('AppTestMarshal.tmp')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def w_marshal_check(self, case):
        import marshal, StringIO
        s = marshal.dumps(case)
        print repr(s)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)
        return x

    def test_None(self):
        case = None
        self.marshal_check(case)

    def test_False(self):
        case = False
        self.marshal_check(case)

    def test_True(self):
        case = True
        self.marshal_check(case)

    def test_StopIteration(self):
        case = StopIteration
        self.marshal_check(case)

    def test_Ellipsis(self):
        case = Ellipsis
        self.marshal_check(case)

    def test_42(self):
        case = 42
        self.marshal_check(case)

    def test__minus_17(self):
        case = -17
        self.marshal_check(case)

    def test_sys_dot_maxint(self):
        import sys
        case = sys.maxint
        self.marshal_check(case)

    def test__minus_1_dot_25(self):
        case = -1.25
        self.marshal_check(case)

    def test__minus_1_dot_25__2(self):
        case = -1.25 #2
        self.marshal_check(case)

    def test_2_plus_5j(self):
        case = 2+5j
        self.marshal_check(case)

    def test_2_plus_5j__2(self):
        case = 2+5j #2
        self.marshal_check(case)

    def test_long(self):
        self.marshal_check(42L)
        case = -1234567890123456789012345678901234567890L
        self.marshal_check(case)

    def test_hello_____not_interned(self):
        hello = "he"
        hello += "llo"
        case = hello   # not interned
        self.marshal_check(case)

    def test__Quote_hello_Quote_(self):
        case = "hello"
        self.marshal_check(case)

    def test__brace__ecarb_(self):
        case = ()
        self.marshal_check(case)

    def test__brace_1_comma__2_ecarb_(self):
        case = (1, 2)
        self.marshal_check(case)

    def test__list__tsil_(self):
        case = []
        self.marshal_check(case)

    def test__list_3_comma__4_tsil_(self):
        case = [3, 4]
        self.marshal_check(case)

    def test__dict__tcid_(self):
        case = {}
        self.marshal_check(case)

    def test__dict_5_colon__6_comma__7_colon__8_tcid_(self):
        case = {5: 6, 7: 8}
        self.marshal_check(case)

    def test_func_dot_func_code(self):
        def func(x):
            return lambda y: x+y
        case = func.func_code
        self.marshal_check(case)

    def test_scopefunc_dot_func_code(self):
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        case = scopefunc.func_code
        self.marshal_check(case)

    def test_u_quote_hello_quote_(self):
        case = u'hello'
        self.marshal_check(case)

    def test_set_brace__ecarb_(self):
        case = set()
        self.marshal_check(case)

    def test_set_brace__list_1_comma__2_tsil__ecarb_(self):
        case = set([1, 2])
        self.marshal_check(case)

    def test_frozenset_brace__ecarb_(self):
        case = frozenset()
        self.marshal_check(case)

    def test_frozenset_brace__list_3_comma__4_tsil__ecarb_(self):
        case = frozenset([3, 4])
        self.marshal_check(case)

    def test_stream_reader_writer(self):
        # for performance, we have a special case when reading/writing real
        # file objects
        import marshal
        obj1 = [4, ("hello", 7.5)]
        obj2 = "foobar"
        f = open(self.tmpfile, 'wb')
        marshal.dump(obj1, f)
        marshal.dump(obj2, f)
        f.write('END')
        f.close()
        f = open(self.tmpfile, 'rb')
        obj1b = marshal.load(f)
        obj2b = marshal.load(f)
        tail = f.read()
        f.close()
        assert obj1b == obj1
        assert obj2b == obj2
        assert tail == 'END'

    def test_unicode(self):
        import marshal, sys
        self.marshal_check(u'\uFFFF')

        self.marshal_check(unichr(sys.maxunicode))

    def test_reject_subtypes(self):
        import marshal
        types = (float, complex, int, long, tuple, list, dict, set, frozenset)
        for cls in types:
            class subtype(cls):
                pass
            raises(ValueError, marshal.dumps, subtype)


class AppTestRope(AppTestMarshal):
    def setup_class(cls):
        from pypy.conftest import gettestobjspace
        cls.space = gettestobjspace(**{"objspace.std.withrope": True})
        AppTestMarshal.setup_class.im_func(cls)

class AppTestSmallLong(AppTestMarshal):
    def setup_class(cls):
        from pypy.conftest import gettestobjspace
        cls.space = gettestobjspace(**{"objspace.std.withsmalllong": True})
        AppTestMarshal.setup_class.im_func(cls)

    def test_smalllong(self):
        import __pypy__
        x = -123456789012345L
        assert 'SmallLong' in __pypy__.internal_repr(x)
        y = self.marshal_check(x)
        assert y == x
        # must be unpickled as a small long
        assert 'SmallLong' in __pypy__.internal_repr(y)
