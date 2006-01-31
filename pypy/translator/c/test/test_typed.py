import autopath
import sys
import py
from py.test import raises
from pypy.translator.test import snippet 
from pypy.rpython.rarithmetic import r_uint, r_longlong, intmask
from pypy.translator.backendopt.raisingop2direct_call import raisingop2direct_call

from pypy.translator.c.test.test_annotated import TestAnnotatedTestCase as _TestAnnotatedTestCase


class TestTypedTestCase(_TestAnnotatedTestCase):

    def process(self, t):
        _TestAnnotatedTestCase.process(self, t)
        t.buildrtyper().specialize()
        raisingop2direct_call(t)

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

    def test_int_div_ovf_zer(self):
        fn = self.getcompiled(snippet.div_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

    def test_int_mul_ovf(self):
        fn = self.getcompiled(snippet.mul_func)
        for y in range(-5, 5):
            for x in range(-5, 5):
                assert fn(x, y) == snippet.mul_func(x, y)
        n = sys.maxint / 4
        assert fn(n, 3) == snippet.mul_func(n, 3)
        assert fn(n, 4) == snippet.mul_func(n, 4)
        raises(OverflowError, fn, n, 5)

    def test_int_mod_ovf_zer(self):
        py.test.skip("XXX does not annotate anymore after raisingops2direct_call transformation")
        fn = self.getcompiled(snippet.mod_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

    def test_int_rshift_val(self):
        fn = self.getcompiled(snippet.rshift_func)
        raises(ValueError, fn, -1)

    def test_int_lshift_ovf_val(self):
        fn = self.getcompiled(snippet.lshift_func)
        raises(ValueError, fn, -1)
        raises(OverflowError, fn, 1)

    def test_int_unary_ovf(self):
        fn = self.getcompiled(snippet.unary_func)
        for i in range(-3,3):
            assert fn(i) == (-(i), abs(i-1))
        raises (OverflowError, fn, -sys.maxint-1)
        raises (OverflowError, fn, -sys.maxint)

    # floats 
    def test_float_operations(self): 
        import math
        def func(x=float, y=float): 
            z = x + y / 2.1 * x 
            z = math.fmod(z, 60.0)
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


    def test_stringformatting(self):
        def fn(i=int):
            return "you said %d, you did"%i
        f = self.getcompiled(fn)
        assert f(1) == fn(1)

    def test_int2str(self):
        def fn(i=int):
            return str(i)
        f = self.getcompiled(fn)
        assert f(1) == fn(1)

    def test_float2str(self):
        def fn(i=float):
            return str(i)
        f = self.getcompiled(fn)
        res = f(1.0)
        assert type(res) is str and float(res) == 1.0
        
    def test_uint_arith(self):
        def fn(i=r_uint):
            try:
                return ~(i*(i+1))/(i-1)
            except ZeroDivisionError:
                return r_uint(91872331)
        f = self.getcompiled(fn)
        for value in range(15):
            i = r_uint(value)
            assert f(i) == fn(i)

    def test_ord_returns_a_positive(self):
        def fn(i=int):
            return ord(chr(i))
        f = self.getcompiled(fn)
        assert f(255) == 255

    def test_hash_preservation(self):
        class C:
            pass
        class D(C):
            pass
        c = C()
        d = D()
        def fn():
            d2 = D()
            x = hash(d2) == id(d2) # xxx check for this CPython peculiarity for now
            return x, hash(c)+hash(d)
        
        f = self.getcompiled(fn)

        res = f()

        from pypy.rpython.rarithmetic import intmask
        
        assert res[0] == True
        assert res[1] == intmask(hash(c)+hash(d))

    def test_list_basic_ops(self):
        def list_basic_ops(i=int, j=int):
            l = [1,2,3]
            l.insert(0, 42)
            del l[1]
            l.append(i)
            listlen = len(l)
            l.extend(l) 
            del l[listlen:]
            l += [5,6] 
            l[1] = i
            return l[j]
        f = self.getcompiled(list_basic_ops)
        for i in range(6): 
            for j in range(6): 
                assert f(i,j) == list_basic_ops(i,j)

    def test_range2list(self):
        def fn():
            r = range(10, 37, 4)
            r.reverse()
            return r[0]
        f = self.getcompiled(fn)
        assert f() == fn()

    def test_range_idx(self):
        def fn(idx=int):
            r = range(10, 37, 4)
            try:
                return r[idx]
            except: raise
        f = self.getcompiled(fn)
        assert f(0) == fn(0)
        assert f(-1) == fn(-1)
        raises(IndexError, f, 42)

    def test_range_step(self):
        def fn(step=int):
            r = range(10, 37, step)
            # we always raise on step = 0
            return r[-2]
        f = self.getcompiled(fn)#, view=True)
        assert f(1) == fn(1)
        assert f(3) == fn(3)
        raises(ValueError, f, 0)

    def test_range_iter(self):
        def fn(start=int, stop=int, step=int):
            res = 0
            if step == 0:
                if stop >= start:
                    r = range(start, stop, 1)
                else:
                    r = range(start, stop, -1)
            else:
                r = range(start, stop, step)
            for i in r:
                res = res * 51 + i
            return res
        f = self.getcompiled(fn)
        for args in [2, 7, 0], [7, 2, 0], [10, 50, 7], [50, -10, -3]:
            assert f(*args) == intmask(fn(*args))

    def test_recursion_detection(self):
        def f(n=int, accum=int):
            if n == 0:
                return accum
            else:
                return f(n-1, accum*n)
        fn = self.getcompiled(f)
        assert fn(7, 1) == 5040
        assert fn(7, 1) == 5040    # detection must work several times, too
        assert fn(7, 1) == 5040
        py.test.raises(RuntimeError, fn, -1, 0)

    def test_list_len_is_true(self):

        class X(object):
            pass
        class A(object):
            def __init__(self):
                self.l = []

            def append_to_list(self, e):
                self.l.append(e)

            def check_list_is_true(self):
                did_loop = 0
                while self.l:
                    did_loop = 1
                    if len(self.l):
                        break
                return did_loop
            
        a1 = A()
        def f():
            for ii in range(1):
                a1.append_to_list(X())
            return a1.check_list_is_true()
        fn = self.getcompiled(f)
        assert fn() == 1
