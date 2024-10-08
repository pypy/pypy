from pypy.conftest import option
from pypy.module.micronumpy import constants as NPY
import platform


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
        else:
            import os
            path = os.path.dirname(__file__) + '/dummy_module.py'
            cls.space.appexec([cls.space.wrap(path)], """(path):
            import imp
            imp.load_source('numpy', path)
            """)
        cls.w_non_native_prefix = cls.space.wrap(NPY.OPPBYTE)
        cls.w_native_prefix = cls.space.wrap(NPY.NATBYTE)
        cls.w_machine = cls.space.newtext(platform.machine())
