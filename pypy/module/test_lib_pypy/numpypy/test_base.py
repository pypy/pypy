class BaseNumpyAppTest(object):
    @classmethod
    def setup_class(cls):
        if cls.runappdirect:
            try:
                import numpy
            except ImportError:
                skip("no numpy found")
            import sys
            sys.modules['numpypy'] = numpy
        else:
            skip("app-level tests")
