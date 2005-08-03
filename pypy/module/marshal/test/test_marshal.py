class AppTestMarshal:

    def test_None(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = None
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_False(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = False
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_True(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = True
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_StopIteration(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = StopIteration
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_Ellipsis(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = Ellipsis
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_42(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 42
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_sys_dot_maxint(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = sys.maxint
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__minus_1_dot_25(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = -1.25
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__minus_1_dot_25__2(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = -1.25 #2
        print "case:", case
        s = marshal.dumps(case, 2); assert len(s) in (9, 17)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_2_plus_5j(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 2+5j
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_2_plus_5j__2(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 2+5j #2
        print "case:", case
        s = marshal.dumps(case, 2); assert len(s) in (9, 17)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_42L(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = 42L
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__minus_1234567890123456789012345678901234567890L(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = -1234567890123456789012345678901234567890L
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_hello_____not_interned(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = hello   # not interned
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__Quote_hello_Quote_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = "hello"
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__open__close_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = ()
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__open_1_comma__2_close_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = (1, 2)
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__list__(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = []
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__list_3_comma__4_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = [3, 4]
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__dict__(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = {}
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test__dict_5_colon__6_comma__7_colon__8_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = {5: 6, 7: 8}
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_func_dot_func_code(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = func.func_code
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_scopefunc_dot_func_code(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = scopefunc.func_code
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_u_quote_hello_quote_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = u'hello'
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_set_open__close_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = set()
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_set_open__list_1_comma__2__close_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = set([1, 2])
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_frozenset_open__close_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = frozenset()
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

    def test_frozenset_open__list_3_comma__4__close_(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = frozenset([3, 4])
        print "case:", case
        s = marshal.dumps(case)
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case

