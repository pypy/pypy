# Collects and executes interpreter-level tests.
#
# Most pypy tests are of this kind.

import py
import sys
from pypy.interpreter.error import OperationError
from pypy.conftest import PyPyClassCollector


def check_keyboard_interrupt(e):
    # we cannot easily convert w_KeyboardInterrupt to KeyboardInterrupt
    # in general without a space -- here is an approximation
    try:
        if e.w_type.name == 'KeyboardInterrupt':
            tb = sys.exc_info()[2]
            raise KeyboardInterrupt, KeyboardInterrupt(), tb
    except AttributeError:
        pass


marker = py.test.mark.interplevel


class IntTestFunction(py.test.collect.Function):
    def __init__(self, *args, **kwargs):
        super(IntTestFunction, self).__init__(*args, **kwargs)
        self._request.applymarker(marker)

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
