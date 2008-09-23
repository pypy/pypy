import autopath


class AppTestBuiltinApp:
    def setup_class(cls):
        class X(object):
            def __eq__(self, other):
                raise OverflowError
            def __hash__(self):
                return 42
        d = {X(): 5}
        try:
            d[X()]
        except OverflowError:
            cls.w_sane_lookup = cls.space.wrap(True)
        except KeyError:
            cls.w_sane_lookup = cls.space.wrap(False)

    def test_import(self):
        m = __import__('pprint')
        assert m.pformat({}) == '{}'
        assert m.__name__ == "pprint"
        raises(ImportError, __import__, 'spamspam')
        raises(TypeError, __import__, 1, 2, 3, 4)

    def test_chr(self):
        assert chr(65) == 'A'
        raises(ValueError, chr, -1)
        raises(TypeError, chr, 'a')

    def test_unichr(self):
        import sys
        assert unichr(65) == u'A'
        assert type(unicode(65)) is unicode
        assert unichr(0x9876) == u'\u9876'
        assert ord(unichr(sys.maxunicode)) == sys.maxunicode
        if sys.maxunicode > 0x10000:
            assert unichr(0x10000) == u'\U00010000'
        raises(ValueError, unichr, -1)
        raises(ValueError, unichr, sys.maxunicode+1)

    def test_intern(self):
        raises(TypeError, intern)
        raises(TypeError, intern, 1)
        class S(str):
            pass
        raises(TypeError, intern, S("hello"))
        s = "never interned before"
        s2 = intern(s)
        assert s == s2
        s3 = s.swapcase()
        assert s3 != s2
        s4 = s3.swapcase()
        assert intern(s4) is s2

    def test_globals(self):
        d = {"foo":"bar"}
        exec "def f(): return globals()" in d
        d2 = d["f"]()
        assert d2 is d

    def test_locals(self):
        def f():
            return locals()
        def g(c=0, b=0, a=0):
            return locals()
        assert f() == {}
        assert g() == {'a':0, 'b':0, 'c':0}

    def test_dir(self):
        def f():
            return dir()
        def g(c=0, b=0, a=0):
            return dir()
        def nosp(x): return [y for y in x if y[0]!='_']
        assert f() == []
        assert g() == ['a', 'b', 'c']
        class X(object): pass
        assert nosp(dir(X)) == []
        class X(object):
            a = 23
            c = 45
            b = 67
        assert nosp(dir(X)) == ['a', 'b', 'c']

    def test_dir_in_broken_locals(self):
        class C(object):
            def __getitem__(self, item):
                raise KeyError(item)
            def keys(self):
                return 'a'    # not a list!
        raises(TypeError, eval, "dir()", {}, C())

    def test_vars(self):
        def f():
            return vars()
        def g(c=0, b=0, a=0):
            return vars()
        assert f() == {}
        assert g() == {'a':0, 'b':0, 'c':0}

    def test_getattr(self):
        class a(object):
            i = 5
        assert getattr(a, 'i') == 5
        raises(AttributeError, getattr, a, 'k')
        assert getattr(a, 'k', 42) == 42
        assert getattr(a, u'i') == 5
        raises(AttributeError, getattr, a, u'k')
        assert getattr(a, u'k', 42) == 42

    def test_getattr_typecheck(self):
        class A(object):
            def __getattribute__(self, name):
                pass
            def __setattr__(self, name, value):
                pass
            def __delattr__(self, name):
                pass
        raises(TypeError, getattr, A(), 42)
        raises(TypeError, setattr, A(), 42, 'x')
        raises(TypeError, delattr, A(), 42)

    def test_sum(self):
        assert sum([]) ==0
        assert sum([42]) ==42
        assert sum([1,2,3]) ==6
        assert sum([],5) ==5
        assert sum([1,2,3],4) ==10

    def test_type_selftest(self):
        assert type(type) is type

    def test_iter_sequence(self):
        raises(TypeError,iter,3)
        x = iter(['a','b','c'])
        assert x.next() =='a'
        assert x.next() =='b'
        assert x.next() =='c'
        raises(StopIteration,x.next)

    def test_iter___iter__(self):
        # This test assumes that dict.keys() method returns keys in
        # the same order as dict.__iter__().
        # Also, this test is not as explicit as the other tests;
        # it tests 4 calls to __iter__() in one assert.  It could
        # be modified if better granularity on the assert is required.
        mydict = {'a':1,'b':2,'c':3}
        assert list(iter(mydict)) ==mydict.keys()

    def test_iter_callable_sentinel(self):
        class count(object):
            def __init__(self):
                self.value = 0
            def __call__(self):
                self.value += 1
                return self.value
        # XXX Raising errors is quite slow --
        #            uncomment these lines when fixed
        #self.assertRaises(TypeError,iter,3,5)
        #self.assertRaises(TypeError,iter,[],5)
        #self.assertRaises(TypeError,iter,{},5)
        x = iter(count(),3)
        assert x.next() ==1
        assert x.next() ==2
        raises(StopIteration,x.next)

    def test_enumerate(self):
        seq = range(2,4)
        enum = enumerate(seq)
        assert enum.next() == (0, 2)
        assert enum.next() == (1, 3)
        raises(StopIteration, enum.next)
        raises(TypeError, enumerate, 1)
        raises(TypeError, enumerate, None)
        

    def test_xrange_args(self):
##        # xrange() attributes are deprecated and were removed in Python 2.3.
##        x = xrange(2)
##        assert x.start == 0
##        assert x.stop == 2
##        assert x.step == 1

##        x = xrange(2,10,2)
##        assert x.start == 2
##        assert x.stop == 10
##        assert x.step == 2

##        x = xrange(2.3, 10.5, 2.4)
##        assert x.start == 2
##        assert x.stop == 10
##        assert x.step == 2

        raises(ValueError, xrange, 0, 1, 0)

    def test_xrange_repr(self): 
        assert repr(xrange(1)) == 'xrange(1)'
        assert repr(xrange(1,2)) == 'xrange(1, 2)'
        assert repr(xrange(1,2,3)) == 'xrange(1, 4, 3)'

    def test_xrange_up(self):
        x = xrange(2)
        iter_x = iter(x)
        assert iter_x.next() == 0
        assert iter_x.next() == 1
        raises(StopIteration, iter_x.next)

    def test_xrange_down(self):
        x = xrange(4,2,-1)

        iter_x = iter(x)
        assert iter_x.next() == 4
        assert iter_x.next() == 3
        raises(StopIteration, iter_x.next)

    def test_xrange_has_type_identity(self):
        assert type(xrange(1)) == type(xrange(1))

    def test_xrange_len(self):
        x = xrange(33)
        assert len(x) == 33
        x = xrange(33.2)
        assert len(x) == 33
        x = xrange(33,0,-1)
        assert len(x) == 33
        x = xrange(33,0)
        assert len(x) == 0
        x = xrange(33,0.2)
        assert len(x) == 0
        x = xrange(0,33)
        assert len(x) == 33
        x = xrange(0,33,-1)
        assert len(x) == 0
        x = xrange(0,33,2)
        assert len(x) == 17
        x = xrange(0,32,2)
        assert len(x) == 16

    def test_xrange_indexing(self):
        x = xrange(0,33,2)
        assert x[7] == 14
        assert x[-7] == 20
        raises(IndexError, x.__getitem__, 17)
        raises(IndexError, x.__getitem__, -18)
        raises(TypeError, x.__getitem__, slice(0,3,1))

    def test_xrange_bad_args(self):
        raises(TypeError, xrange, '1')
        raises(TypeError, xrange, None)
        raises(TypeError, xrange, 3+2j)
        raises(TypeError, xrange, 1, '1')
        raises(TypeError, xrange, 1, 3+2j)
        raises(TypeError, xrange, 1, 2, '1')
        raises(TypeError, xrange, 1, 2, 3+2j)
    
    def test_sorted(self):
        l = []
        sorted_l = sorted(l)
        assert sorted_l is not l
        assert sorted_l == l
        l = [1, 5, 2, 3]
        sorted_l = sorted(l)
        assert sorted_l == [1, 2, 3, 5]

    def test_sorted_with_keywords(self):
        l = ['a', 'C', 'b']
        sorted_l = sorted(l, reverse = True)
        assert sorted_l is not l
        assert sorted_l == ['b', 'a', 'C']
        sorted_l = sorted(l, reverse = True, key = lambda x: x.lower())
        assert sorted_l is not l
        assert sorted_l == ['C', 'b', 'a']
        
    def test_reversed_simple_sequences(self):
        l = range(5)
        rev = reversed(l)
        assert list(rev) == [4, 3, 2, 1, 0]
        assert list(l.__reversed__()) == [4, 3, 2, 1, 0]
        s = "abcd"
        assert list(reversed(s)) == ['d', 'c', 'b', 'a']

    def test_reversed_custom_objects(self):
        """make sure __reversed__ is called when defined"""
        class SomeClass(object):
            def __reversed__(self):
                return 42
        obj = SomeClass()
        assert reversed(obj) == 42
    
        
    def test_cmp(self):
        assert cmp(9,9) == 0
        assert cmp(0,9) < 0
        assert cmp(9,0) > 0
        assert cmp("abc", 12) != 0
        assert cmp(u"abc", 12) != 0

    def test_cmp_more(self):
        class C(object):
            def __eq__(self, other):
                return True
            def __cmp__(self, other):
                raise RuntimeError
        c1 = C()
        c2 = C()
        raises(RuntimeError, cmp, c1, c2)

    def test_cmp_cyclic(self):
        if not self.sane_lookup:
            skip("underlying Python implementation has insane dict lookup")
        a = []; a.append(a)
        b = []; b.append(b)
        from UserList import UserList
        c = UserList(); c.append(c)
        raises(RuntimeError, cmp, a, b)
        raises(RuntimeError, cmp, b, c)
        raises(RuntimeError, cmp, c, a)
        raises(RuntimeError, cmp, a, c)
        # okay, now break the cycles
        a.pop(); b.pop(); c.pop()
        
    def test_coerce(self):
        assert coerce(1, 2)    == (1, 2)
        assert coerce(1L, 2L)  == (1L, 2L)
        assert coerce(1, 2L)   == (1L, 2L)
        assert coerce(1L, 2)   == (1L, 2L)
        assert coerce(1, 2.0)  == (1.0, 2.0)
        assert coerce(1.0, 2L) == (1.0, 2.0)
        assert coerce(1L, 2.0) == (1.0, 2.0)
        raises(TypeError,coerce, 1    , 'a')
        raises(TypeError,coerce, u'a' , 'a')

    def test_return_None(self):
        class X(object): pass
        x = X()
        assert setattr(x, 'x', 11) == None
        assert delattr(x, 'x') == None
        # To make this test, we need autopath to work in application space.
        #self.assertEquals(execfile('emptyfile.py'), None)

    def test_divmod(self):
        assert divmod(15,10) ==(1,5)

    def test_callable(self):
        class Call(object):
            def __call__(self, a):
                return a+2
        assert callable(Call()), (
                    "Builtin function 'callable' misreads callable object")
        assert callable(int), (
                    "Builtin function 'callable' misreads int")
        class Call:
            def __call__(self, a):
                return a+2
        assert callable(Call())


    def test_uncallable(self):
        # XXX TODO: I made the NoCall class explicitly newstyle to try and
        # remedy the failure in this test observed when running this with
        # the trivial objectspace, but the test _still_ fails then (it
        # doesn't fail with the standard objectspace, though).
        class NoCall(object):
            pass
        a = NoCall()
        assert not callable(a), (
                    "Builtin function 'callable' misreads uncallable object")
        a.__call__ = lambda: "foo"
        assert not callable(a), (
                    "Builtin function 'callable' tricked by instance-__call__")
        class NoCall:
            pass
        assert not callable(NoCall())

    def test_hash(self):
        assert hash(23) == hash(23)
        assert hash(2.3) == hash(2.3)
        assert hash('23') == hash("23")
        assert hash((23,)) == hash((23,))
        assert hash(22) != hash(23)
        raises(TypeError, hash, [])
        raises(TypeError, hash, {})

    def test_eval(self):
        assert eval("1+2") == 3
        assert eval(" \t1+2\n") == 3
        assert eval("len([])") == 0
        assert eval("len([])", {}) == 0        
        # cpython 2.4 allows this (raises in 2.3)
        assert eval("3", None, None) == 3
        i = 4
        assert eval("i", None, None) == 4

    def test_compile(self):
        co = compile('1+2', '?', 'eval')
        assert eval(co) == 3
        raises(SyntaxError, compile, '-', '?', 'eval')
        raises(ValueError, compile, '"\\xt"', '?', 'eval')
        raises(ValueError, compile, '1+2', '?', 'maybenot')
        raises(TypeError, compile, '1+2', 12, 34)

    def test_unicode_compile(self):
        try:
            compile(u'-', '?', 'eval')
        except SyntaxError, e:
            assert e.lineno == 1
            
    def test_isinstance(self):
        assert isinstance(5, int)
        assert isinstance(5, object)
        assert not isinstance(5, float)
        assert isinstance(True, (int, float))
        assert not isinstance(True, (type, float))
        assert isinstance(True, ((type, float), bool))
        raises(TypeError, isinstance, 5, 6)
        raises(TypeError, isinstance, 5, (float, 6))

    def test_issubclass(self):
        assert issubclass(int, int)
        assert issubclass(int, object)
        assert not issubclass(int, float)
        assert issubclass(bool, (int, float))
        assert not issubclass(bool, (type, float))
        assert issubclass(bool, ((type, float), bool))
        raises(TypeError, issubclass, 5, int)
        raises(TypeError, issubclass, int, 6)
        raises(TypeError, issubclass, int, (float, 6))

    def test_staticmethod(self):
        class X(object):
            def f(*args, **kwds): return args, kwds
            f = staticmethod(f)
        assert X.f() == ((), {})
        assert X.f(42, x=43) == ((42,), {'x': 43})
        assert X().f() == ((), {})
        assert X().f(42, x=43) == ((42,), {'x': 43})

    def test_classmethod(self):
        class X(object):
            def f(*args, **kwds): return args, kwds
            f = classmethod(f)
        class Y(X):
            pass
        assert X.f() == ((X,), {})
        assert X.f(42, x=43) == ((X, 42), {'x': 43})
        assert X().f() == ((X,), {})
        assert X().f(42, x=43) == ((X, 42), {'x': 43})
        assert Y.f() == ((Y,), {})
        assert Y.f(42, x=43) == ((Y, 42), {'x': 43})
        assert Y().f() == ((Y,), {})
        assert Y().f(42, x=43) == ((Y, 42), {'x': 43})

    def test_hasattr(self):
        class X(object):
            def broken(): pass   # TypeError
            abc = property(broken)
            def broken2(): raise IOError
            bac = property(broken2)
        x = X()
        x.foo = 42
        assert hasattr(x, '__class__') is True
        assert hasattr(x, 'foo') is True
        assert hasattr(x, 'bar') is False
        assert hasattr(x, 'abc') is False    # CPython compliance
        assert hasattr(x, 'bac') is False    # CPython compliance
        raises(TypeError, hasattr, x, None)
        raises(TypeError, hasattr, x, 42)
        raises(UnicodeError, hasattr, x, u'\u5678')  # cannot encode attr name

class AppTestBuiltinOptimized(object):
    def setup_class(cls):
        from pypy.conftest import gettestobjspace
        cls.space = gettestobjspace(**{"objspace.opcodes.CALL_LIKELY_BUILTIN": True})

    # hum, we need to invoke the compiler explicitely
    def test_xrange_len(self):
        s = """def test():
        x = xrange(33)
        assert len(x) == 33
        x = xrange(33.2)
        assert len(x) == 33
        x = xrange(33,0,-1)
        assert len(x) == 33
        x = xrange(33,0)
        assert len(x) == 0
        x = xrange(33,0.2)
        assert len(x) == 0
        x = xrange(0,33)
        assert len(x) == 33
        x = xrange(0,33,-1)
        assert len(x) == 0
        x = xrange(0,33,2)
        assert len(x) == 17
        x = xrange(0,32,2)
        assert len(x) == 16
        """
        ns = {}
        exec s in ns
        ns["test"]()

    def test_delete_from_builtins(self):
        s = """ """
        # XXX write this test!

    def test_shadow_case_bound_method(self):
        s = """def test(l):
        n = len(l)
        old_len = len
        class A(object):
            x = 5
            def length(self, o):
                return self.x*old_len(o)
        import __builtin__
        __builtin__.len = A().length
        try:
            m = len(l)
        finally:
            __builtin__.len = old_len
        return n+m
        """
        ns = {}
        exec s in ns
        res = ns["test"]([2,3,4])
        assert res == 18
        

class TestInternal:

    def setup_method(self,method):
        space = self.space

    def get_builtin(self, name):
        return self.space.builtin.get(name) 

    def test_execfile(self):
        from pypy.tool.udir import udir
        fn = str(udir.join('test_execfile'))
        f = open(fn, 'w')
        print >>f, "i=42"
        f.close()

        w_execfile = self.get_builtin('execfile')
        space = self.space
        w_dict = space.newdict()
        self.space.call_function(w_execfile,
            space.wrap(fn), w_dict, space.w_None)
        w_value = space.getitem(w_dict, space.wrap('i'))
        assert self.space.eq_w(w_value, space.wrap(42))

    def test_execfile_different_lineendings(self): 
        space = self.space
        from pypy.tool.udir import udir
        d = udir.ensure('lineending', dir=1)
        dos = d.join('dos.py') 
        f = dos.open('wb') 
        f.write("x=3\r\n\r\ny=4\r\n")
        f.close() 
        space.appexec([space.wrap(str(dos))], """
            (filename): 
                d = {}
                execfile(filename, d)
                assert d['x'] == 3
                assert d['y'] == 4
        """)

        unix = d.join('unix.py')
        f = unix.open('wb') 
        f.write("x=5\n\ny=6\n")
        f.close() 

        space.appexec([space.wrap(str(unix))], """
            (filename): 
                d = {}
                execfile(filename, d)
                assert d['x'] == 5
                assert d['y'] == 6
        """)
