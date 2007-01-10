import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_exception import BaseTestException
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.rpython.test.test_rpbc import BaseTestRPBC
from pypy.rpython.test.test_rtuple import BaseTestRtuple
from pypy.rpython.test.test_rstr import BaseTestRstr

class TestJsException(JsTest, BaseTestException):
    pass

class TestJsClass(JsTest, BaseTestRclass):
    def test_common_class_attribute(self):
        py.test.skip("WIP")
    
    def test___class___attribute(self):
        py.test.skip("unsuitable")
    
    def test_mixin(self):
        py.test.skip("unsuitable")
        
    def test_getattr_on_classes(self):
        py.test.skip("WIP")
        
    def test_hash_preservation(self):
        py.test.skip("WIP")

    def test_issubclass_type(self):
        py.test.skip("WIP")
    
    def test_isinstance(self):
        py.test.skip("WIP")
    
    def test_recursive_prebuilt_instance_classattr(self):
        py.test.skip("WIP")

#class TestJsList(JsTest, BaseTestRlist):
#    def test_insert_bug(self):
#        py.test.skip("in progress")
##    
#class TestJsPBC(JsTest, BaseTestRPBC):
#    pass
##
#class TestJsRtuple(JsTest, BaseTestRtuple):
#    pass
##
#class TestJsStr(JsTest, BaseTestRstr):
#    pass
