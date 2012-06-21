from __future__ import with_statement
"""
This file is OBSCURE.  Really.  The purpose is to avoid copying and changing
'test_c.py' from cffi/c/.
"""
import py
from pypy.tool.udir import udir
from pypy.conftest import gettestobjspace
from pypy.interpreter import gateway
from pypy.module._ffi_backend.test import _backend_test_c
from pypy.module._ffi_backend import Module


class AppTestC(object):
    """Populated below, hack hack hack."""


def find_and_load_library_for_test(space, w_name):
    import ctypes.util
    path = ctypes.util.find_library(space.str_w(w_name))
    return space.appexec([space.wrap(path)], """(path):
        import _ffi_backend
        return _ffi_backend.load_library(path)""")


space = gettestobjspace(usemodules=('_ffi_backend',))
src = py.path.local(__file__).join('..', '_backend_test_c.py').read()
w_func = space.wrap(gateway.interp2app(find_and_load_library_for_test))
all_names = ', '.join(Module.interpleveldefs.keys())
w_namespace = space.appexec([w_func], "(func):" +
                            '\n    from _ffi_backend import %s' % all_names +
                            '\n    class py:' +
                            '\n        class test:' +
                            '\n            raises = staticmethod(raises)' +
                            src.replace('\n', '\n    ') +
                            '\n    find_and_load_library = func' +
                            '\n    return locals()\n')
AppTestC.w_namespace = w_namespace

lst = []
for name in space.unwrap(space.call_function(space.w_list, w_namespace)):
    if name.startswith('test_'):
        lst.append(getattr(_backend_test_c, name))
lst.sort(key=lambda func: func.func_code.co_firstlineno)

tmpname = udir.join('_test_c.py')
with tmpname.open('w') as f:
    for func in lst:
        print >> f, 'def %s(self):' % (func.__name__,)
        print >> f, '    func = self.namespace[%r]' % (func.__name__,)
        print >> f, '    func()'

mod = tmpname.pyimport()
for key, value in mod.__dict__.items():
    if key.startswith('test_'):
        setattr(AppTestC, key, value)
