import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_exception import BaseTestException
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.rpython.test.test_rpbc import BaseTestRPBC
from pypy.rpython.test.test_rtuple import BaseTestRtuple
from pypy.rpython.test.test_rstr import BaseTestRstr

##from pypy.rpython.test.test_rrange import BaseTestRrange
##from pypy.rpython.test.test_rbool import BaseTestRbool
##from pypy.rpython.test.test_rfloat import BaseTestRfloat
##from pypy.rpython.test.test_rint import BaseTestRint
##from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin
##from pypy.rpython.test.test_rdict import BaseTestRdict
##from pypy.rpython.test.test_objectmodel import BaseTestObjectModel
##from pypy.rpython.test.test_remptydict import BaseTestRemptydict
##from pypy.rpython.test.test_rconstantdict import BaseTestRconstantdict
##from pypy.rpython.test.test_rspecialcase import BaseTestRspecialcase

class TestCliException(CliTest, BaseTestException):
    pass


class TestCliClass(CliTest, BaseTestRclass):
    def test_recursive_prebuilt_instance(self):
        py.test.skip("gencli doesn't support recursive constants, yet")


class TestCliPBC(CliTest, BaseTestRPBC):
    def test_call_memoized_cache(self):
        py.test.skip("gencli doesn't support recursive constants, yet")        

    def test_specialized_method_of_frozen(self):
        py.test.skip("waiting to be fixed")


class TestCliList(CliTest, BaseTestRlist):
    def test_recursive(self):
        py.test.skip("CLI doesn't support recursive lists")
        

class TestCliTuple(CliTest, BaseTestRtuple):
    def test_constant_unichar_tuple_contains(self):
        py.test.skip("CLI doesn't support cast_int_to_unichar, yet")


class TestCliString(CliTest, BaseTestRstr):
    def test_char_isxxx(self):
        def fn(s):
            return (s.isspace()      |
                    s.isdigit() << 1 |
                    s.isalpha() << 2 |
                    s.isalnum() << 3 |
                    s.isupper() << 4 |
                    s.islower() << 5)
        # need to start from 1, because we cannot pass '\x00' as a command line parameter        
        for i in range(1, 128):
            ch = chr(i)
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_unichar_const(self):
        py.test.skip("CLI interpret doesn't support unicode for input arguments")
    test_unichar_eq = test_unichar_const
    test_unichar_ord = test_unichar_const
    test_unichar_hash = test_unichar_const

    def test_upper(self):
        py.test.skip("CLI doens't support backquotes inside string literals")
    test_lower = test_upper

    def test_replace_TyperError(self):
        pass # it doesn't make sense here

    def test_int(self):
        py.test.skip("CLI doesn't support integer parsing, yet")
    test_int_valueerror = test_int
