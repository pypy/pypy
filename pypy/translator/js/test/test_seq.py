from __future__ import division
import py

from pypy.objspace.flow.model import Constant, Variable
from pypy.translator.js.test.runtest import compile_function
from pypy.translator.llvm.test import llvmsnippet

class TestList(object):
    def test_normal_list(self):
        def normal_list():
            l = [1,2,3]
            return l[1]
        
        fn = compile_function(normal_list, [])
        assert fn() == 2
    
    def test_var_list(self):
        def var_list():
            l = []
            for i in xrange(10):
                l.append(i)
            return l[8]
        
        fn = compile_function(var_list, [])
        assert fn() == 8
    
    def test_slice(self):
        def l_test():
            l = []
            for i in xrange(10):
                l.append(i)
            return len(l[3:8])
        
        fn = compile_function(l_test, [])
        assert fn() == l_test()
    
    def test_init_0(self):
        def l_init():
            l = [0] * 100
            return l[38]
        
        fn = compile_function(l_init, [])
        assert fn() == 0

class TestDict(object):
    def test_dict_iter(self):
        def dict_iter():
            sum = 0
            d = {'a':3, 'b':4, 'c':8}
            for k in d:
                sum += d[k]
            return sum
        
        fn = compile_function(dict_iter, [])
        assert fn() == dict_iter()
    
    def test_const_dict(self):
        c = {'aa':'asd', 'ab':'ds', 'ac':'asddsa', 'ad':'sadsad', 'ae':'sadsa'}
            
        def const_dict(ind):
            return c[ind]
        
        fn = compile_function(const_dict, [str])
        for i in c.keys():
            assert fn(i) == const_dict(i)
    
    def test_sophisticated_const(self):
        c = {'aa':1, 'bb':2, 'cc':3, 'dd':4}
        c1 = {'fff' : 'aa', 'zzz' : 'bb', 'xxx' : 'cc', 'bbb' : 'dd'}
        c2 = {'xxx' : 'aa', 'kkk' : 'bb', 'aaaa' : 'cc', 'www' : 'dd'}
        def soph_const(i1, i2):
            return c1[i1] + c2[i2]
        
        fn = compile_function(soph_const, [str, str])
        for x in c1.keys():
            for y in c2.keys():
                assert fn(x, y) == soph_const(x, y)

    def test_dict_iterator(self):
        c = {'aa':1, 'bb':2, 'cc':3, 'dd':4}
        def dict_iter():
            sum = 0
            for i in c:
                sum += c[i]
            return sum

        fn = compile_function(dict_iter, [])
        assert fn() == dict_iter()

class TestTuple(object):
    def test_f1(self):
        f = compile_function(llvmsnippet.tuple_f1, [int])
        assert f(10) == 10
        assert f(15) == 15

    def test_f3(self):
        f = compile_function(llvmsnippet.tuple_f3, [int])
        assert f(10) == 10
        assert f(15) == 15
        assert f(30) == 30

    def test_constant_tuple(self):
        f = compile_function(llvmsnippet.constant_tuple, [int])
        for i in range(3, 7):
            assert f(i) == i + 3

class TestString(object):
    def test_upperlower(self):
        def upperlower():
            s = "aBaF"
            return s.upper() + s.lower()
        
        fn = compile_function(upperlower, [])
        assert fn() == "ABAFabaf"
    
    def test_slice(self):
        def one_slice(s):
            return s[1:]
            
        def two_slice(s):
            return s[2:]
        
        fn = compile_function(one_slice, [str])
        assert fn("dupa") == "upa"
        fn = compile_function(two_slice, [str])
        assert fn("kupa") == "pa"

def test_simple_seq():
    def fun(i):
        if i:
            a = [("ab", "cd"), ("ef", "xy")]
        else:
            a = [("xz", "pr"), ("as", "fg")]
        return ",".join(["%s : %s" % (i, j) for i,j in a])
    
    fn = compile_function(fun, [int])
    assert fn(0) == fun(0)
    assert fn(1) == fun(1)
