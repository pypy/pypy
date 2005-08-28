from pypy.module.marshal import interp_marshal
from pypy.interpreter.error import OperationError
import sys


class AppTestMarshalMore:

    def test_long_0(self):
        import marshal
        z = 0L
        z1 = marshal.loads(marshal.dumps(z))
        assert z == z1
