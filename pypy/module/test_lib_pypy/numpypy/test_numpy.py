from pypy.conftest import option
import py, sys
from pypy.module.test_lib_pypy.numpypy.test_base import BaseNumpyAppTest

class AppTestNumpy(BaseNumpyAppTest):
    def test_min_max_after_import(self):
        import __builtin__
        from __builtin__ import *

        from numpypy import *
        assert min is __builtin__.min
        assert max is __builtin__.max

        assert min(1, 100) == 1
        assert min(100, 1) == 1

        assert max(1, 100) == 100
        assert max(100, 1) == 100

        assert min(4, 3, 2, 1) == 1
        assert max(1, 2, 3, 4) == 4

        from numpypy import min, max, amin, amax
        assert min is not __builtin__.min
        assert max is not __builtin__.max
        assert min is amin
        assert max is amax

    def test_builtin_aliases(self):
        import __builtin__
        import numpypy
        from numpypy import *

        for name in ['bool', 'int', 'long', 'float', 'complex', 'object',
                     'unicode', 'str']:
            assert name not in locals()
            assert getattr(numpypy, name) is getattr(__builtin__, name)

    def test_typeinfo(self):
        import numpypy
        assert 'typeinfo' not in dir(numpypy)
        assert 'typeinfo' in dir(numpypy.core.multiarray)

    def test_set_string_function(self):
        import numpypy
        assert numpypy.set_string_function is not \
               numpypy.core.multiarray.set_string_function

    def test_constants(self):
        import math
        import numpypy
        assert numpypy.PZERO == numpypy.NZERO == 0.0
        assert math.isinf(numpypy.inf)
        assert math.isnan(numpypy.nan)

    def test___all__(self):
        import numpypy
        assert '__all__' in dir(numpypy)
        assert 'numpypy' not in dir(numpypy)

    def test_get_include(self):
        import numpypy, os, sys
        assert 'get_include' in dir(numpypy)
        path = numpypy.get_include()
        if not hasattr(sys, 'pypy_translation_info'):
            skip("pypy white-box test")
        assert os.path.exists(path + '/numpy/arrayobject.h')
