import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rlib.test.test_rarithmetic import Test_r_uint as BaseTest_r_uint
from pypy.rlib.test.test_rarithmetic import Test_r_int as BaseTest_r_int
from pypy.rlib.test.test_rarithmetic import test_ovfcheck as base_test_ovfcheck
from pypy.rlib import rarithmetic as ra

class BaseAdaptedTest(JvmTest):
    
    def unary_test(self, f):
        cache = {}
        def new_func(x):
            xtype = type(x)
            if xtype == self.RTYPE:
                if xtype not in cache:
                    fun = self.compile(f, [x], None)
                    cache[xtype] = fun
                return cache[xtype](x)
            return f(x)
        super(BaseAdaptedTest,self).unary_test(new_func)    
        
    def binary_test(self, f, rargs = None):
        cache = {}
        def new_func(x, y):
            if type(x) == self.RTYPE or type(y) == self.RTYPE:
                types = (type(x), type(y))
                if types not in cache:
                    fun = self.compile(f, [x, y], None)
                    cache[types] = fun
                return cache[types](x, y)
            return f(x,y)
        super(BaseAdaptedTest,self).binary_test(new_func, rargs)

class Test_r_uint(BaseAdaptedTest, BaseTest_r_uint):
    RTYPE = ra.r_uint    
    def test__pow__(self):
        py.test.skip("rpython has no ** on ints")
    def test__divmod__(self):
        # to enable this, you must first replace the call to binary_test(divmod)
        # with binary_test(lambda x, y: divmod(x,y)), but even then you run into
        # problems
        py.test.skip("divmod not fully supported by rtyper")
        
#class Test_r_int(BaseAdaptedTest, BaseTest_r_int):
#    RTYPE = ra.r_int
#    def test__pow__(self):
#        py.test.skip("rpython has no ** on ints")
#    def test__divmod__(self):
#        py.test.skip("divmod not fully supported by rtyper")

