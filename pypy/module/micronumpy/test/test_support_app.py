"""App-level tests for support.py"""
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestSupport(BaseNumpyAppTest):
    def test_add_docstring(self):
        import numpy as np
        foo = lambda: None
        np.add_docstring(foo, "Does a thing")
        assert foo.__doc__ == "Does a thing"

    def test_type_docstring(self):
        # XXX: We cannot sensibly test np.add_docstring() being successful
        import numpy as np
        import types
        raises(RuntimeError, np.add_docstring, types.FunctionType, 'foo')

    def test_method_docstring(self):
        # XXX: We cannot sensibly test np.add_docstring() being successful
        import numpy as np
        #raises(RuntimeError, np.add_docstring, int.bit_length, 'foo')
        np.add_docstring(int.bit_length,'foo')
        assert int.bit_length.__doc__ == 'foo'
