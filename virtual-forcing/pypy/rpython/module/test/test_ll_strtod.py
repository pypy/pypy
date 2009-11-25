import py

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib import rarithmetic

class BaseTestStrtod(BaseRtypingTest):    
    def test_formatd(self):
        def f(y):
            return rarithmetic.formatd("%.2f", y)

        assert self.ll_to_string(self.interpret(f, [3.0])) == f(3.0)

    def test_parts_to_float(self):
        from pypy.rpython.annlowlevel import hlstr
        
        def f(a, b, c, d):
            a,b,c,d = hlstr(a), hlstr(b), hlstr(c), hlstr(d)
            
            return rarithmetic.parts_to_float(a, b, c, d)
        
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
