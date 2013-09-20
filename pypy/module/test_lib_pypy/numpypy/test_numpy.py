from pypy.conftest import option
import py, sys
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestNumpyImport1(object):
    spaceconfig = dict(usemodules=['micronumpy'])

    @classmethod
    def setup_class(cls):
        if option.runappdirect and '__pypy__' not in sys.builtin_module_names:
            py.test.skip("pypy only test")

    def test_imports_no_warning(self):
        from warnings import catch_warnings
        with catch_warnings(record=True) as w:
            import numpypy
            import numpy
            assert len(w) == 0
            import numpy
            assert len(w) == 0

class AppTestNumpyImport2(object):
    spaceconfig = dict(usemodules=['micronumpy'])

    @classmethod
    def setup_class(cls):
        if option.runappdirect and '__pypy__' not in sys.builtin_module_names:
            py.test.skip("pypy only test")

    def test_imports_with_warning(self):
        import sys
        from warnings import catch_warnings
        # XXX why are numpypy and numpy modules already imported?
        mods = [d for d in sys.modules.keys() if d.find('numpy') >= 0]
        if mods:
            skip('%s already imported' % mods)

        with catch_warnings(record=True) as w:
            import numpy
            msg = w[0].message
            assert msg.message.startswith(
                "The 'numpy' module of PyPy is in-development")
            import numpy
            assert len(w) == 1

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
        import numpy
        assert '__all__' in numpy
        assert 'numpypy' not in dir(numpy)

    def test_get_include(self):
        import numpy, os
        assert 'get_include' in dir(numpy)
        path = numpy.get_include()
        assert os.path.exists(path + '/numpy/arrayobject.h')
