import autopath


class AppTestBuiltinApp:
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

    def test_intern(self):
        raises(TypeError, intern)
        raises(TypeError, intern, 1)
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
        class X: pass
        assert nosp(dir(X)) == []
        class X:
            a = 23
            c = 45
            b = 67
        assert nosp(dir(X)) == ['a', 'b', 'c']

    def test_vars(self):
        def f():
            return vars()
        def g(c=0, b=0, a=0):
            return vars()
        assert f() == {}
        assert g() == {'a':0, 'b':0, 'c':0}

    def test_getattr(self):
        class a:
            i = 5
        assert getattr(a, 'i') == 5
        raises(AttributeError, getattr, a, 'k')
        assert getattr(a, 'k', 42) == 42
        assert getattr(a, u'i') == 5
        raises(AttributeError, getattr, a, u'k')
        assert getattr(a, u'k', 42) == 42

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
        class SomeClass:
            def __reversed__(self):
                return 42
        obj = SomeClass()
        assert reversed(obj) == 42
    
        
    def test_cmp(self):
        assert cmp(9,9) == 0
        assert cmp(0,9) < 0
        assert cmp(9,0) > 0

    def test_cmp_more(self):
        class C:
            def __eq__(self, other):
                return True
            def __cmp__(self, other):
                raise RuntimeError
        c1 = C()
        c2 = C()
        raises(RuntimeError, cmp, c1, c2)

    def test_cmp_cyclic(self):
        a = []; a.append(a)
        b = []; b.append(b)
        from UserList import UserList
        c = UserList(); c.append(c)
        assert cmp(a, b) == 0
        assert cmp(b, c) == 0
        assert cmp(c, a) == 0
        assert cmp(a, c) == 0
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
        class X: pass
        x = X()
        assert setattr(x, 'x', 11) == None
        assert delattr(x, 'x') == None
        # To make this test, we need autopath to work in application space.
        #self.assertEquals(execfile('emptyfile.py'), None)

    def test_divmod(self):
        assert divmod(15,10) ==(1,5)

    def test_callable(self):
        class Call:
            def __call__(self, a):
                return a+2
        assert not not callable(Call()), (
                    "Builtin function 'callable' misreads callable object")
        assert callable(int), (
                    "Builtin function 'callable' misreads int")

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

    def test_compile(self):
        co = compile('1+2', '?', 'eval')
        assert eval(co) == 3
        raises(SyntaxError, compile, '-', '?', 'eval')
        raises(ValueError, compile, '"\\xt"', '?', 'eval')
        raises(ValueError, compile, '1+2', '?', 'maybenot')
        raises(TypeError, compile, '1+2', 12, 34)

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
        class X:
            def f(*args, **kwds): return args, kwds
            f = staticmethod(f)
        assert X.f() == ((), {})
        assert X.f(42, x=43) == ((42,), {'x': 43})
        assert X().f() == ((), {})
        assert X().f(42, x=43) == ((42,), {'x': 43})

    def test_classmethod(self):
        class X:
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


class TestInternal:

    def setup_method(self,method):
        space = self.space

    def get_builtin(self, name):
        w = self.space.wrap
        w_builtins = self.space.w_builtins
        w_obj = self.space.getitem(w_builtins, w(name))
        return w_obj

    def test_execfile(self):
        from pypy.tool.udir import udir
        fn = str(udir.join('test_execfile'))
        f = open(fn, 'w')
        print >>f, "i=42"
        f.close()

        w_execfile = self.get_builtin('execfile')
        space = self.space
        w_dict = space.newdict([])
        self.space.call_function(w_execfile,
            space.wrap(fn), w_dict, space.w_None)
        w_value = space.getitem(w_dict, space.wrap('i'))
        assert self.space.eq_w(w_value, space.wrap(42))
