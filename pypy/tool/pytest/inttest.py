# Collects and executes interpreter-level tests.
#
# Most pypy tests are of this kind.

import py
from pypy.interpreter.error import OperationError
from pypy.conftest import PyPyClassCollector


class IntTestFunction(py.test.collect.Function):
    def __init__(self, *args, **kwargs):
        super(IntTestFunction, self).__init__(*args, **kwargs)
        self.keywords['interplevel'] = True

    def runtest(self):
        try:
            super(IntTestFunction, self).runtest()
        except OperationError, e:
            check_keyboard_interrupt(e)
            raise
        except Exception, e:
            cls = e.__class__
            while cls is not Exception:
                if cls.__name__ == 'DistutilsPlatformError':
                    from distutils.errors import DistutilsPlatformError
                    if isinstance(e, DistutilsPlatformError):
                        py.test.skip('%s: %s' % (e.__class__.__name__, e))
                cls = cls.__bases__[0]
            raise


class IntInstanceCollector(py.test.collect.Instance):
    Function = IntTestFunction


class IntClassCollector(PyPyClassCollector):
    Instance = IntInstanceCollector

    def _haskeyword(self, keyword):
        return (keyword == 'interplevel' or 
                super(IntClassCollector, self)._haskeyword(keyword))

    def _keywords(self):
        return super(IntClassCollector, self)._keywords() + ['interplevel']

