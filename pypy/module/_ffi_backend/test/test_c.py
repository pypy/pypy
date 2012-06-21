from __future__ import with_statement
import py
from pypy.tool.udir import udir
from pypy.conftest import gettestobjspace
from pypy.module._ffi_backend.test import _backend_test_c


class AppTestC(object):
    """Populated below, hack hack hack."""


space = gettestobjspace(usemodules=('_ffi_backend',))
src = py.path.local(__file__).join('..', '_backend_test_c.py').read()
w_namespace = space.appexec([], "():\n" +
                            src.replace('\n', '\n    ') +
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
