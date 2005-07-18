import autopath
import sys
from py.test import raises
from pypy.translator.translator import Translator
from pypy.translator.test import snippet 
from pypy.translator.tool.buildpyxmodule import skip_missing_compiler

from pypy.translator.c.test.test_annotated import TestAnnotatedTestCase as _TestAnnotatedTestCase


class TestTypedTestCase(_TestAnnotatedTestCase):

    def getcompiled(self, func):
        t = Translator(func, simplifying=True)
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        a = t.annotate(argstypelist)
        a.simplify()
        t.specialize()
        t.checkgraphs()
        return skip_missing_compiler(t.ccompile)

    def test_call_five(self):
        # --  the result of call_five() isn't a real list, but an rlist
        #     that can't be converted to a PyListObject
        def wrapper():
            lst = snippet.call_five()
            return len(lst), lst[0]
        call_five = self.getcompiled(wrapper)
        result = call_five()
        assert result == (1, 5)

    def test_get_set_del_slice(self):
        def get_set_del_nonneg_slice(): # no neg slices for now!
            l = [ord('a'), ord('b'), ord('c'), ord('d'), ord('e'), ord('f'), ord('g'), ord('h'), ord('i'), ord('j')]
            del l[:1]
            bound = len(l)-1
            if bound >= 0:
                del l[bound:]
            del l[2:4]
            #l[:1] = [3]
            #bound = len(l)-1
            #assert bound >= 0
            #l[bound:] = [9]    no setting slice into lists for now
            #l[2:4] = [8,11]
            l[0], l[-1], l[2], l[3] =3, 9, 8, 11

            list_3_c = l[:2]
            list_9 = l[5:]
            list_11_h = l[3:5]
            return (len(l), l[0], l[1], l[2], l[3], l[4], l[5],
                    len(list_3_c),  list_3_c[0],  list_3_c[1],
                    len(list_9),    list_9[0],
                    len(list_11_h), list_11_h[0], list_11_h[1])
        fn = self.getcompiled(get_set_del_nonneg_slice)
        result = fn()
        assert result == (6, 3, ord('c'), 8, 11, ord('h'), 9,
                          2, 3, ord('c'),
                          1, 9,
                          2, 11, ord('h'))

    def test_is(self):
        def testfn():
            l1 = []
            return l1 is l1
        fn = self.getcompiled(testfn)
        result = fn()
        assert result is True
        def testfn():
            l1 = []
            return l1 is None
        fn = self.getcompiled(testfn)
        result = fn()
        assert result is False

    def test_str_compare(self):
        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] == s2[j]
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(6):
                res = fn(i, j)
                assert res is testfn(i, j)

        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] != s2[j]
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(6):
                res = fn(i, j)
                assert res is testfn(i, j)
                
        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] < s2[j]
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(6):
                res = fn(i, j)
                assert res is testfn(i, j)
                
        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] <= s2[j]
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(6):
                res = fn(i, j)
                assert res is testfn(i, j)
                
        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] > s2[j]
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(6):
                res = fn(i, j)
                assert res is testfn(i, j)
                
        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] >= s2[j]
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(6):
                res = fn(i, j)
                assert res is testfn(i, j)
                
    def test_str_methods(self):
        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
            return s1[i].startswith(s2[j])
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(9):
                res = fn(i, j)
                assert res is testfn(i, j)
        def testfn(i=int, j=int):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
            return s1[i].endswith(s2[j])
        fn = self.getcompiled(testfn)
        for i in range(2):
            for j in range(9):
                res = fn(i, j)
                assert res is testfn(i, j)

    def test_str_join(self):
        def testfn(i=int, j=int):
            s1 = [ '', ',', ' and ']
            s2 = [ [], ['foo'], ['bar', 'baz', 'bazz']]
            return s1[i].join(s2[j])
        fn = self.getcompiled(testfn)
        for i in range(3):
            for j in range(3):
                res = fn(i, j)
                assert res == fn(i, j)
    
    def test_unichr_eq(self):
        l = list(u'Hello world')
        def f(i=int,j=int):
            return l[i] == l[j]
        fn = self.getcompiled(f)
        for i in range(len(l)):
            for j in range(len(l)):
                res = fn(i,j)
                assert res == f(i,j) 
    
    def test_unichr_ne(self):
        l = list(u'Hello world')
        def f(i=int,j=int):
            return l[i] != l[j]
        fn = self.getcompiled(f)
        for i in range(len(l)):
            for j in range(len(l)):
                res = fn(i,j)
                assert res == f(i,j)

    def test_unichr_ord(self):
        l = list(u'Hello world')
        def f(i=int):
            return ord(l[i]) 
        fn = self.getcompiled(f)
        for i in range(len(l)):
            res = fn(i)
            assert res == f(i)

    def test_unichr_unichr(self):
        l = list(u'Hello world')
        def f(i=int, j=int):
            return l[i] == unichr(j)
        fn = self.getcompiled(f)
        for i in range(len(l)):
            for j in range(len(l)):
                res = fn(i, ord(l[j]))
                assert res == f(i, ord(l[j]))

    def test_slice_long(self):
        "the parent's test_slice_long() makes no sense here"

    def test_int_overflow(self):
        fn = self.getcompiled(snippet.add_func)
        raises(OverflowError, fn, sys.maxint)

    def test_int_div_ovf_zer(self): # 
        fn = self.getcompiled(snippet.div_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

    def test_int_mod_ovf_zer(self):
        fn = self.getcompiled(snippet.mod_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

##    def test_int_rshift_val(self):
##        fn = self.getcompiled(snippet.rshift_func)
##        raises(ValueError, fn, -1)

##    def test_int_lshift_ovf_val(self):
##        fn = self.getcompiled(snippet.lshift_func)
##        raises(ValueError, fn, -1)
##        raises(OverflowError, fn, 1)

    def test_int_unary_ovf(self):
        fn = self.getcompiled(snippet.unary_func)
        for i in range(-3,3):
            assert fn(i) == (-(i), abs(i-1))
        raises (OverflowError, fn, -sys.maxint-1)
        raises (OverflowError, fn, -sys.maxint)

    # floats 
    def test_float_operations(self): 
        def func(x=float, y=float): 
            z = x + y / 2.1 * x 
            z = z % 60.0
            z = pow(z, 2)
            z = -z
            return int(z) 

        fn = self.getcompiled(func)
        assert fn(5.0, 6.0) == func(5.0, 6.0) 

    def test_rpbc_bound_method_static_call(self):
        class R:
            def meth(self):
                return 0
        r = R()
        m = r.meth
        def fn():
            return m()
        res = self.getcompiled(fn)()
        assert res == 0

    def test_constant_return_disagreement(self):
        class R:
            def meth(self):
                return 0
        r = R()
        def fn():
            return r.meth()
        res = self.getcompiled(fn)()
        assert res == 0

    def test_math_exp(self):
        from math import exp
        def fn(f=float):
            return exp(f)
        f = self.getcompiled(fn)
        assert f(1.0) == exp(1.0)

    def test_stringformatting(self):
        def fn(i=int):
            return "you said %d, you did"%i
        f = self.getcompiled(fn)
        assert f(1) == fn(1)

    def test_str2int(self):
        def fn(i=int):
            return str(i)
        f = self.getcompiled(fn)
        assert f(1) == fn(1)

    def test_float2int(self):
        def fn(i=float):
            return str(i)
        f = self.getcompiled(fn)
        assert f(1.0) == fn(1.0)
        
