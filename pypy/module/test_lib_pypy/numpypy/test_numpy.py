from pypy.conftest import gettestobjspace

class AppTestNumpy:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['micronumpy'])

    def test_imports(self):
        try:
            import numpy   # fails if 'numpypy' was not imported so far
        except ImportError:
            pass
        import numpypy
        import numpy     # works after 'numpypy' has been imported
