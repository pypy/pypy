from pypy.translator.cli.test.runtest import CliTest
<<<<<<< .mine
from pypy.translator.cli.test.runtest import check
from pypy.rlib.rarithmetic import r_uint, r_ulonglong, r_longlong, ovfcheck
from pypy.rpython import rstack
from pypy.annotation import model as annmodel
import sys
=======
from pypy.translator.oosupport.test_template.operations import BaseTestOperations
>>>>>>> .r33967

class TestOperations(CliTest, BaseTestOperations):
    pass
