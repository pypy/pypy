import py

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib import rfloat

class BaseTestStrtod(BaseRtypingTest):    
    def test_formatd(self):
        for flags in [0,
                      rfloat.DTSF_ADD_DOT_0]:
            def f(y):
                return rfloat.formatd(y, 'g', 2, flags)

            assert self.ll_to_string(self.interpret(f, [3.0])) == f(3.0)

    def test_parts_to_float(self):
        from pypy.rpython.annlowlevel import hlstr
        
        def f(a, b, c, d):
            a,b,c,d = hlstr(a), hlstr(b), hlstr(c), hlstr(d)
            
            return rfloat.parts_to_float(a, b, c, d)
        
        data = [
        (("","1","","")     , 1.0),
        (("-","1","","")    , -1.0),
        (("-","1","5","")   , -1.5),
        (("-","1","5","2")  , -1.5e2),
        (("-","1","5","+2") , -1.5e2),
        (("-","1","5","-2") , -1.5e-2),
        ]

        for parts, val in data:
            args = [self.string_to_ll(i) for i in parts]
            assert self.interpret(f, args) == val

class TestLLStrtod(BaseTestStrtod, LLRtypeMixin):
    pass
