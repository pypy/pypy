import sys
import py
from py.test import raises
from pypy.translator.test import snippet 
from pypy.rlib.rarithmetic import r_uint, ovfcheck, ovfcheck_lshift

from pypy.translator.js.test.runtest import compile_function

def test_call_five():
    def wrapper():
        lst = snippet.call_five()
        res = list((len(lst), lst[0]))
        expected = [1, 5]
        return res == expected
    fn = compile_function(wrapper, [])
    result = fn()
    assert result == wrapper()

def test_get_set_del_slice():
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
        l[0], l[-1], l[2], l[3] = 3, 9, 8, 11

        list_3_c = l[:2]
        list_9 = l[5:]
        list_11_h = l[3:5]
        return list((len(l), l[0], l[1], l[2], l[3], l[4], l[5],
                     len(list_3_c),  list_3_c[0],  list_3_c[1],
                     len(list_9),    list_9[0],
                     len(list_11_h), list_11_h[0], list_11_h[1]))
    
    def wrapper():
        res = get_set_del_nonneg_slice()
        expected = [6, 3, ord('c'), 8, 11, ord('h'), 9,
                    2, 3, ord('c'),
                    1, 9,
                    2, 11, ord('h')]
    
        return res == expected

    fn = compile_function(wrapper, [])
    result = fn()
    assert result 

def test_is():
    def testfn():
        l1 = []
        return l1 is l1
    fn = compile_function(testfn, [])
    result = fn()
    assert result == True
    def testfn():
        l1 = []
        return l1 is None
    fn = compile_function(testfn, [])
    result = fn()
    assert result == False

def test_nones():
    a = [None] * 4
    def nones():        
        a.append(None)
        return len(a)
    fn = compile_function(nones, [])
    result = fn()
    assert result == 4

def test_str_compare():
    def testfn_eq(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] == s2[j]
    fn = compile_function(testfn_eq, [int, int])
    for i in range(2):
        for j in range(6):
            res = fn(i, j)
            assert res == testfn_eq(i, j)

    def testfn_ne(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] != s2[j]
    fn = compile_function(testfn_ne, [int, int])
    for i in range(2):
        for j in range(6):
            res = fn(i, j)
            assert res == testfn_ne(i, j)

    def testfn_lt(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] < s2[j]
    fn = compile_function(testfn_lt, [int, int])
    for i in range(2):
        for j in range(6):
            res = fn(i, j)
            assert res == testfn_lt(i, j)

    def testfn_le(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] <= s2[j]
    fn = compile_function(testfn_le, [int, int])
    for i in range(2):
        for j in range(6):
            res = fn(i, j)
            assert res == testfn_le(i, j)

    def testfn_gt(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] > s2[j]
    fn = compile_function(testfn_gt, [int, int])
    for i in range(2):
        for j in range(6):
            res = fn(i, j)
            assert res == testfn_gt(i, j)

    def testfn_ge(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] >= s2[j]
    fn = compile_function(testfn_ge, [int, int])
    for i in range(2):
        for j in range(6):
            res = fn(i, j)
            assert res == testfn_ge(i, j)

def test_str_methods():
    def testfn_startswith(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
        return s1[i].startswith(s2[j])
    fn = compile_function(testfn_startswith, [int, int])
    for i in range(2):
        for j in range(9):
            res = fn(i, j)
            assert res == testfn_startswith(i, j)

    def testfn_endswith(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
        return s1[i].endswith(s2[j])
    fn = compile_function(testfn_endswith, [int, int])
    for i in range(2):
        for j in range(9):
            res = fn(i, j)
            assert res == testfn_endswith(i, j)

def test_str_join():
    #py.test.skip("stringBuilder support")
    def testfn(i, j):
        s1 = [ '', ',', ' and ']
        s2 = [ [], ['foo'], ['bar', 'baz', 'bazz']]
        return len(s1[i].join(s2[j]))

    fn = compile_function(testfn, [int, int])
    for i in range(3):
        for j in range(3):
            res = fn(i, j)
            assert res == testfn(i, j)

def test_unichr_eq():
    #py.test.skip("Unicode support")
    l = list(u'Hello world')
    def f(i, j):
        return l[i] == l[j]
    fn = compile_function(f, [int, int])
    for i in range(len(l)):
        for j in range(len(l)):
            res = fn(i, j)
            assert res == f(i,j) 

def test_unichr_ne():
    #py.test.skip("Unicode support")
    l = list(u'Hello world')
    def f(i, j):
        return l[i] != l[j]
    fn = compile_function(f, [int, int])
    for i in range(len(l)):
        for j in range(len(l)):
            res = fn(i, j)
            assert res == f(i, j)

def test_unichr_ord():
    #py.test.skip("ord semantics")
    #py.test.skip("Unicode support")
    l = list(u'Hello world')
    def f(i):
        return ord(l[i]) 
    fn = compile_function(f, [int])
    for i in range(len(l)):
        res = fn(i)
        assert res == f(i)

def test_unichr_unichr():
    #py.test.skip("Unicode support")
    l = list(u'Hello world')
    def f(i, j):
        return l[i] == unichr(j)
    fn = compile_function(f, [int, int])
    for i in range(len(l)):
        for j in range(len(l)):
            res = fn(i, ord(l[j]))
            assert res == f(i, ord(l[j]))

# floats 
def test_float_operations():
    #py.test.skip("issue with ll_math_fmod calling itself")
    import math
    def func(x, y): 
        z = x + y / 2.1 * x 
        z = math.fmod(z, 60.0)
        z = math.pow(z, 2)
        z = -z
        return int(z)

    fn = compile_function(func, [float, float])
    r1 = fn(5.0, 6.0)
    r2 = func(5.0, 6.0)
    assert r1 == r2-1   #-1 for stupid spidermonkey rounding error

def test_rpbc_bound_method_static_call():
    class R:
        def meth(self):
            return 0
    r = R()
    m = r.meth
    def fn():
        return m()
    res = compile_function(fn, [])()
    assert res == 0

def test_constant_return_disagreement():
    class R:
        def meth(self):
            return 0
    r = R()
    def fn():
        return r.meth()
    res = compile_function(fn, [])()
    assert res == 0

def test_stringformatting():
    #py.test.skip("StringBuilder not implemented")
    def fn(i):
        return "you said %d, you did" % i
    def wrapper(i):
        res = fn(i)
        return res == "you said 42, you did"

    f = compile_function(wrapper, [int])
    assert f(42)

def test_int2str():
    def fn(i):
        return str(i)
    def wrapper(i):
        res = fn(i)
        return res == "42"

    f = compile_function(wrapper, [int])
    assert f(42)

def test_int_invert():
    def fn(i):
        return ~i
    f = compile_function(fn, [int])
    for i in range(-15, 15):
        assert f(i) == fn(i)

def DONTtest_uint_invert(): #issue with Javascript Number() having a larger range
    def fn(i):
        inverted = ~i
        inverted -= sys.maxint
        return inverted
    f = compile_function(fn, [r_uint])
    for value in range(1, 15):
        i = r_uint(value)
        assert str(f(i)) == str(fn(i))
    s = 0xfffffff    
    for value in range(s, s+1024, 64):
        i = r_uint(value)
        assert str(f(i)) == str(fn(i))

def test_int_abs():
    def int_abs_(n):
        return abs(n)
    f = compile_function(int_abs_, [int])
    for i in (-25, 0, 75):
        assert f(i) == int_abs_(i)

def test_float_abs():
    def float_abs_(n):
        return abs(n)
    f = compile_function(float_abs_, [float])
    for i in (-100.1 -50.2, -0.0, 0.0, 25.3, 50.4):
        assert f(i) == float_abs_(i)

def test_cast_to_int():
    def casting(v):
        return int(ord(chr(v)))
    f = compile_function(casting, [int])
    for ii in range(255):
        assert f(ii) == ii

def test_char_comparisons():
    #py.test.skip("chr/ord semantics")
    def comps(v):
        x = chr(v)
        res = 0
        res += x < chr(0)
        res += x > chr(1)
        res += x >= chr(127)
        res += x < chr(128)
        res += x < chr(250)
        return res
    f = compile_function(comps, [int])
    for ii in range(255):
        assert f(ii) == comps(ii)
