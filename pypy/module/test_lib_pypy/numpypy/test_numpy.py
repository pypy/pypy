from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestNumpy(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=['micronumpy'])

    def test_imports(self):
        try:
            import numpy   # fails if 'numpypy' was not imported so far
        except ImportError:
            pass
        import numpypy
        import numpy     # works after 'numpypy' has been imported

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
