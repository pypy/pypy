from pypy.tool.udir import udir

class AppTestMarshal:

    def setup_class(cls):
        tmpfile = udir.join('AppTestMarshal.tmp')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def test_None(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = None
        print "case: %-30s   func=None" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_False(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = False
        print "case: %-30s   func=False" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_True(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = True
        print "case: %-30s   func=True" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_StopIteration(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = StopIteration
        print "case: %-30s   func=StopIteration" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_Ellipsis(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = Ellipsis
        print "case: %-30s   func=Ellipsis" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_42(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 42
        print "case: %-30s   func=42" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__minus_17(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = -17
        print "case: %-30s   func=_minus_17" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_sys_dot_maxint(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = sys.maxint
        print "case: %-30s   func=sys_dot_maxint" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__minus_1_dot_25(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = -1.25
        print "case: %-30s   func=_minus_1_dot_25" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__minus_1_dot_25__2(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = -1.25 #2
        print "case: %-30s   func=_minus_1_dot_25__2" % (case, )
        s = marshal.dumps(case, 2); assert len(s) in (9, 17)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_2_plus_5j(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 2+5j
        print "case: %-30s   func=2_plus_5j" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_2_plus_5j__2(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 2+5j #2
        print "case: %-30s   func=2_plus_5j__2" % (case, )
        s = marshal.dumps(case, 2); assert len(s) in (9, 17)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_42L(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 42L
        print "case: %-30s   func=42L" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__minus_1234567890123456789012345678901234567890L(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = -1234567890123456789012345678901234567890L
        print "case: %-30s   func=_minus_1234567890123456789012345678901234567890L" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_hello_____not_interned(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = hello   # not interned
        print "case: %-30s   func=hello_____not_interned" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__Quote_hello_Quote_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = "hello"
        print "case: %-30s   func=_Quote_hello_Quote_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__brace__ecarb_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = ()
        print "case: %-30s   func=_brace__ecarb_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__brace_1_comma__2_ecarb_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = (1, 2)
        print "case: %-30s   func=_brace_1_comma__2_ecarb_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__list__tsil_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = []
        print "case: %-30s   func=_list__tsil_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__list_3_comma__4_tsil_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = [3, 4]
        print "case: %-30s   func=_list_3_comma__4_tsil_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__dict__tcid_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = {}
        print "case: %-30s   func=_dict__tcid_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test__dict_5_colon__6_comma__7_colon__8_tcid_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = {5: 6, 7: 8}
        print "case: %-30s   func=_dict_5_colon__6_comma__7_colon__8_tcid_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_func_dot_func_code(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = func.func_code
        print "case: %-30s   func=func_dot_func_code" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_scopefunc_dot_func_code(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = scopefunc.func_code
        print "case: %-30s   func=scopefunc_dot_func_code" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_u_quote_hello_quote_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = u'hello'
        print "case: %-30s   func=u_quote_hello_quote_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_set_brace__ecarb_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = set()
        print "case: %-30s   func=set_brace__ecarb_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_set_brace__list_1_comma__2_tsil__ecarb_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = set([1, 2])
        print "case: %-30s   func=set_brace__list_1_comma__2_tsil__ecarb_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_frozenset_brace__ecarb_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = frozenset()
        print "case: %-30s   func=frozenset_brace__ecarb_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

    def test_frozenset_brace__list_3_comma__4_tsil__ecarb_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = frozenset([3, 4])
        print "case: %-30s   func=frozenset_brace__list_3_comma__4_tsil__ecarb_" % (case, )
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case and type(x) is type(case)
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)

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


class AppTestMultiDict(object):
    def setup_class(cls):
        from pypy.conftest import gettestobjspace
        cls.space = gettestobjspace(**{"objspace.std.withmultidict": True})

    test__dict__tcid_ = AppTestMarshal.test__dict__tcid_.im_func
    test__dict_5_colon__6_comma__7_colon__8_tcid_ = AppTestMarshal.test__dict_5_colon__6_comma__7_colon__8_tcid_.im_func

class AppTestRope(AppTestMarshal):
    def setup_class(cls):
        from pypy.conftest import gettestobjspace
        cls.space = gettestobjspace(**{"objspace.std.withrope": True})
        AppTestMarshal.setup_class.im_func(cls)
