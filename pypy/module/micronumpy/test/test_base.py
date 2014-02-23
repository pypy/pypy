from pypy.module.micronumpy import constants as NPY
from pypy.conftest import option

class BaseNumpyAppTest(object):
    spaceconfig = dict(usemodules=['micronumpy'])

    @classmethod
    def setup_class(cls):
        if option.runappdirect:
            import sys
            if '__pypy__' not in sys.builtin_module_names:
                import numpy
            else:
                from . import dummy_module as numpy
                sys.modules['numpy'] = numpy
            sys.modules['numpypy'] = numpy
        else:
            import os
            path = os.path.dirname(__file__) + '/dummy_module.py'
            cls.space.appexec([cls.space.wrap(path)], """(path):
            import imp
            numpy = imp.load_source('numpy', path)
            import sys
            sys.modules['numpypy'] = numpy
            """)
        cls.w_non_native_prefix = cls.space.wrap(NPY.OPPBYTE)
        cls.w_native_prefix = cls.space.wrap(NPY.NATBYTE)
