import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_exception import BaseTestException
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.rpython.test.test_rpbc import BaseTestRPBC
from pypy.rpython.test.test_rtuple import BaseTestRtuple

##from pypy.rpython.test.test_rbool import BaseTestRbool
##from pypy.rpython.test.test_rfloat import BaseTestRfloat
##from pypy.rpython.test.test_rint import BaseTestRint
##from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin
##from pypy.rpython.test.test_rrange import BaseTestRrange
##from pypy.rpython.test.test_rstr import BaseTestRstr
##from pypy.rpython.test.test_rdict import BaseTestRdict
##from pypy.rpython.test.test_objectmodel import BaseTestObjectModel
##from pypy.rpython.test.test_remptydict import BaseTestRemptydict
##from pypy.rpython.test.test_rconstantdict import BaseTestRconstantdict
##from pypy.rpython.test.test_rspecialcase import BaseTestRspecialcase

class xTestCliException(CliTest, BaseTestException):
    pass


class xTestCliClass(CliTest, BaseTestRclass):
    def test_recursive_prebuilt_instance(self):
        py.test.skip("gencli doesn't support recursive constants, yet")


class xTestCliPBC(CliTest, BaseTestRPBC):
    def test_call_memoized_cache(self):
        py.test.skip("gencli doesn't support recursive constants, yet")        

    def test_multiple_specialized_functions(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_specialized_method_of_frozen(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_specialized_method(self):
        py.test.skip("CLI doesn't support string, yet")


class xTestCliList(CliTest, BaseTestRlist):
    def test_recursive(self):
        py.test.skip("CLI doesn't support recursive lists")

    def test_list_comparestr(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_not_a_char_list_after_all(self):
        py.test.skip("CLI doesn't support string, yet")
        
    def test_list_str(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_inst_list(self):
        py.test.skip("CLI doesn't support string, yet")

class TestCliTuple(CliTest, BaseTestRtuple):
    def test_constant_tuple_contains(self):
        py.test.skip("CLI doesn't support dict, yet")

    test_constant_tuple_contains2 = test_constant_tuple_contains
    test_constant_unichar_tuple_contains = test_constant_tuple_contains

    def test_inst_tuple_add_getitem(self):
        py.test.skip("Need to fix pending nodes rendering")

