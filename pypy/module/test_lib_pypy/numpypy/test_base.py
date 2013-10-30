class BaseNumpyAppTest(object):
    @classmethod
    def setup_class(cls):
        if cls.runappdirect:
            import numpy
            import sys
            sys.modules['numpypy'] = numpy
        else:
            skip("app-level tests")
