import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_exception import BaseTestException
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.rpython.test.test_rpbc import BaseTestRPBC
from pypy.rpython.test.test_rtuple import BaseTestRtuple
from pypy.rpython.test.test_rstr import BaseTestRstr

#py.test.skip("Test in progress")

class TestJsException(JsTest, BaseTestException):
    pass

class TestJsClass(JsTest, BaseTestRclass):
    def test_classattr_as_defaults(self):
        py.test.skip("WIP")
    
    def test_recursive_prebuilt_instance(self):
        py.test.skip("WIP")
    
    def test_common_class_attribute(self):
        py.test.skip("WIP")
    
    def test___class___attribute(self):
        py.test.skip("WIP")
    
    def test_mixin(self):
        py.test.skip("WIP")
    
    def test_type(self):
        py.test.skip("WIP")
    
    def test_hash_preservation(self):
        py.test.skip("WIP")
    
    def test_ne(self):
        py.test.skip("WIP")
    
    def test_eq(self):
        py.test.skip("WIP")
    
    def test_issubclass_type(self):
        py.test.skip("WIP")
    
    def test_isinstance(self):
        py.test.skip("WIP")
    
    def test_recursive_prebuilt_instance_classattr(self):
        py.test.skip("WIP")

##class TestJsList(JsTest, BaseTestRlist):
##    pass
##    
##class TestJsPBC(JsTest, BaseTestRPBC):
##    pass
##
##class TestJsRtuple(JsTest, BaseTestRtuple):
##    pass
##
##class TestJsStr(JsTest, BaseTestRstr):
##    pass
