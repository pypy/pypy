import autopath

from pypy.tool import test

class TestBuiltinApp(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace()
    
    def test_sign(self):
        self.assertEquals(sign(-4), -1)
        self.assertEquals(sign(0), 0)
        self.assertEquals(sign(10), 1)

    def test_import(self):
        m = __import__('pprint')
        self.assertEquals(m.pformat({}), '{}')
        self.assertEquals(m.__name__, "pprint")
        self.assertRaises(ImportError, __import__, 'spamspam')
        self.assertRaises(TypeError, __import__, 1, 2, 3, 4)

    def test_chr(self):
        self.assertEquals(chr(65), 'A')
        self.assertRaises(ValueError, chr, -1)
        self.assertRaises(TypeError, chr, 'a')

    def test_intern(self):
        self.assertRaises(TypeError, intern)
        self.assertRaises(TypeError, intern, 1)
        s = "never interned before"
        s2 = intern(s)
        self.assertEquals(s, s2)
        s3 = s.swapcase()
        self.assert_(s3 != s2)
        s4 = s3.swapcase()
        self.assert_(intern(s4) is s2)

    def test_globals(self):
        d = {"foo":"bar"}
        exec "def f(): return globals()" in d
        d2 = d["f"]()
        self.assertEquals(d2,d)

    def test_locals(self):
        def f():
            return locals()
        def g(c=0, b=0, a=0):
            return locals()
        self.assertEquals(f(), {})
        self.assertEquals(g(), {'a':0, 'b':0, 'c':0})
        
    def test_dir(self):
        def f():
            return dir()
        def g(c=0, b=0, a=0):
            return dir()
        def nosp(x): return [y for y in x if y[0]!='_']
        self.assertEquals(f(), [])
        self.assertEquals(g(), ['a', 'b', 'c'])
        class X: pass
        self.assertEquals(nosp(dir(X)), nosp(['__module__', ]))
        class X: a = 23
        self.assertEquals(nosp(dir(X)), nosp(['__module__', 'a']))
        class X:
            a = 23
            c = 45
            b = 67
        self.assertEquals(nosp(dir(X)), nosp(['__module__', 'a', 'b', 'c']))

    def test_vars(self):
        def f():
            return vars()
        def g(c=0, b=0, a=0):
            return vars()
        self.assertEquals(f(), {})
        self.assertEquals(g(), {'a':0, 'b':0, 'c':0})
        
    def test_getattr(self):
        class a: 
            i = 5
        self.assertEquals(getattr(a, 'i'), 5)
        self.assertRaises(AttributeError, getattr, a, 'k')
        self.assertEquals(getattr(a, 'k', 42), 42)

    def test_sum(self):
        self.assertEquals(sum([]),0)
        self.assertEquals(sum([42]),42)
        self.assertEquals(sum([1,2,3]),6)
        self.assertEquals(sum([],5),5)
        self.assertEquals(sum([1,2,3],4),10)
        
    def test_type_selftest(self):
        self.assert_(type(type) is type)

    def test_iter_sequence(self):
        self.assertRaises(TypeError,iter,3)
        x = iter(['a','b','c'])
        self.assertEquals(x.next(),'a')
        self.assertEquals(x.next(),'b')
        self.assertEquals(x.next(),'c')
        self.assertRaises(StopIteration,x.next)

    def test_iter___iter__(self):
        # This test assumes that dict.keys() method returns keys in
        # the same order as dict.__iter__().
        # Also, this test is not as explicit as the other tests;
        # it tests 4 calls to __iter__() in one assert.  It could
        # be modified if better granularity on the assert is required.
        mydict = {'a':1,'b':2,'c':3}
        self.assertEquals(list(iter(mydict)),mydict.keys())

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
        self.assertEquals(x.next(),1)
        self.assertEquals(x.next(),2)
        self.assertRaises(StopIteration,x.next)
        
    def test_enumerate(self):
        seq = range(2,4)
        enum = enumerate(seq)
        self.assertEquals(enum.next(), (0, 2))
        self.assertEquals(enum.next(), (1, 3))
        self.assertRaises(StopIteration, enum.next)
        
    def test_xrange_args(self):
        x = xrange(2)
        self.assertEquals(x.start, 0)
        self.assertEquals(x.stop, 2)
        self.assertEquals(x.step, 1)

        x = xrange(2,10,2)
        self.assertEquals(x.start, 2)
        self.assertEquals(x.stop, 10)
        self.assertEquals(x.step, 2)

        self.assertRaises(ValueError, xrange, 0, 1, 0) 

    def test_xrange_up(self):
        x = xrange(2)
        self.assertEquals(x.start, 0)
        self.assertEquals(x.stop, 2)
        self.assertEquals(x.step, 1)

        iter_x = iter(x)
        self.assertEquals(iter_x.next(), 0)
        self.assertEquals(iter_x.next(), 1)
        self.assertRaises(StopIteration, iter_x.next)

    def test_xrange_down(self):
        x = xrange(4,2,-1)

        iter_x = iter(x)
        self.assertEquals(iter_x.next(), 4)
        self.assertEquals(iter_x.next(), 3)
        self.assertRaises(StopIteration, iter_x.next)

    def test_xrange_has_type_identity(self):
        self.assertEquals(type(xrange(1)), type(xrange(1)))

    def test_cmp(self):
        self.assertEquals(cmp(9,9), 0)
        self.assert_(cmp(0,9) < 0)
        self.assert_(cmp(9,0) > 0)

    def test_return_None(self):
        self.assertEquals(setattr(self, 'x', 11), None)
        self.assertEquals(delattr(self, 'x'), None)
        # To make this test, we need autopath to work in application space.
        #self.assertEquals(execfile('emptyfile.py'), None)

    def test_divmod(self):
        self.assertEquals(divmod(15,10),(1,5))

        
class TestInternal(test.IntTestCase):

    def setUp(self):
        self.space = space = test.objspace()

    def get_builtin(self, name):
        w = self.space.wrap
        w_builtins = self.space.w_builtins
        w_obj = self.space.getitem(w_builtins, w(name))
        return w_obj
   
    def test_execfile(self):
        # we need cpython's tempfile currently to test 
        from tempfile import mktemp
        fn = mktemp()
        f = open(fn, 'w')
        print >>f, "i=42"
        f.close()

        try:
            w_execfile = self.get_builtin('execfile')
            space = self.space
            w_dict = space.newdict([])
            self.space.call(w_execfile, space.newtuple([
                space.wrap(fn), w_dict, space.w_None]), space.newdict([]))
            w_value = space.getitem(w_dict, space.wrap('i'))
            self.assertEqual_w(w_value, space.wrap(42))
        finally:
            import os
            os.remove(fn)

    def test_xrange(self):
        self.assert_(hasattr(self.space.builtin, 'xrange'))
        self.assertEquals(self.space.builtin.xrange(3).stop, 3)

    def test_callable(self):
        class Call:
            def __call__(self, a):
                return a+2
        self.failIf(not callable(Call()),
                    "Builtin function 'callable' misreads callable object")
        self.assert_(callable(int),
                    "Builtin function 'callable' misreads int")

    def test_uncallable(self):
        class NoCall:
            pass
        a = NoCall()
        self.failIf(callable(a),
                    "Builtin function 'callable' misreads uncallable object")
        a.__call__ = lambda: "foo"
        self.failIf(callable(a), 
                    "Builtin function 'callable' tricked by instance-__call__")


if __name__ == '__main__':
    test.main()
 
