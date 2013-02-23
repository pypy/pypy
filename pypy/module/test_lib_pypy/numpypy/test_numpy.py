class AppTestNumpy:
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
