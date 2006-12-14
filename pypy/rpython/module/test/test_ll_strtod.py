import py

class BaseTest(object):
    
    def test_parts_to_float(self):
        #py.test.skip("wip")
        Support = self.Support
        Impl = self.Implementation
        
        data = [
        (("","1","","")     , 1.0),
        (("-","1","","")    , -1.0),
        (("-","1","5","")   , -1.5),
        (("-","1","5","2")  , -1.5e2),
        (("-","1","5","+2") , -1.5e2),
        (("-","1","5","-2") , -1.5e-2),
        ]

        for parts, val in data:
            assert Impl.ll_strtod_parts_to_float(*map(Support.to_rstr, parts)) == val


    def test_formatd(self):
        Support = self.Support
        Impl = self.Implementation
        
        res = Impl.ll_strtod_formatd(Support.to_rstr("%.2f"), 1.5)
        assert Support.from_rstr(res) == "1.50"

class TestLL(BaseTest):
    from pypy.rpython.module.support import LLSupport as Support
    from pypy.rpython.lltypesystem.module.ll_strtod import Implementation

class TestOO(BaseTest):
    from pypy.rpython.module.support import OOSupport as Support
    from pypy.rpython.ootypesystem.module.ll_strtod import Implementation
