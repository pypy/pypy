from pypy.module.micronumpy.interp_dtype import NPY_NATBYTE, NPY_OPPBYTE
from pypy.conftest import option
import sys

class BaseNumpyAppTest(object):
    spaceconfig = dict(usemodules=['micronumpy'])

    @classmethod
    def setup_class(cls):
        if option.runappdirect:
            if '__pypy__' not in sys.builtin_module_names:
                import numpy
                sys.modules['numpypy'] = numpy
        cls.w_non_native_prefix = cls.space.wrap(NPY_OPPBYTE)
        cls.w_native_prefix = cls.space.wrap(NPY_NATBYTE)
