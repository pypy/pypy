import py
import pypy
import pypy.module
from pypy.module.sys.version import CPYTHON_VERSION

LIB_ROOT = py.path.local(pypy.__path__[0]).dirpath()
LIB_PYPY =  LIB_ROOT.join('lib_pypy')
LIB_PYTHON = LIB_ROOT.join('lib-python')
LIB_PYTHON_VANILLA = LIB_PYTHON.join('%d.%d' % CPYTHON_VERSION[:2])
LIB_PYTHON_MODIFIED = LIB_PYTHON.join('modified-%d.%d' % CPYTHON_VERSION[:2])


def import_from_lib_pypy(modname):
    modname = LIB_PYPY.join(modname+'.py')
    return modname.pyimport()
