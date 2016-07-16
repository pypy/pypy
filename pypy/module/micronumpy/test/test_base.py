from pypy.conftest import option
from pypy.module.micronumpy import constants as NPY


class BaseNumpyAppTest(object):
    spaceconfig = dict(usemodules=["micronumpy", "struct", "binascii"])

    @classmethod
    def setup_class(cls):
        if option.runappdirect:
            import sys
            if '__pypy__' not in sys.builtin_module_names:
                import numpy
            else:
                from . import dummy_module as numpy
                sys.modules['numpy'] = numpy
                # override Unpickler.find_class
                def find_class(self, module, name):
                    if (module == 'numpy.core.multiarray' and 
                                    name == '_reconstruct'):
                        return numpy.ndarray.__new__
                    __import__(module)
                    mod = sys.modules[module]
                    klass = getattr(mod, name)
                    return klass

                from pickle import Unpickler
                Unpickler.find_class = find_class

                from cPickle import Unpickler
                Unpickler.find_class = find_class
        else:
            import os
            path = os.path.dirname(__file__) + '/dummy_module.py'
            cls.space.appexec([cls.space.wrap(path)], """(path):
            import imp
            import sys
            numpy = imp.load_source('numpy', path)
            # override Unpickler.find_class
            def find_class(self, module, name):
                if module == 'numpy.core.multiarray' and name == '_reconstruct':
                    return numpy.ndarray.__new__
                __import__(module)
                mod = sys.modules[module]
                klass = getattr(mod, name)
                return klass

            from pickle import Unpickler
            Unpickler.find_class = find_class

            from cPickle import Unpickler
            Unpickler.find_class = find_class
            """)
        cls.w_non_native_prefix = cls.space.wrap(NPY.OPPBYTE)
        cls.w_native_prefix = cls.space.wrap(NPY.NATBYTE)
