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

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ffi_backend',))
        cls.space = space
        def find_and_load_library_for_test(space, w_name):
            import ctypes.util
            path = ctypes.util.find_library(space.str_w(w_name))
            return space.appexec([space.wrap(path)], """(path):
                import _ffi_backend
                return _ffi_backend.load_library(path)""")
        w_func = space.wrap(gateway.interp2app(find_and_load_library_for_test))
        space.appexec([space.wrap(str(tmpdir)), w_func],
        """(path, func):
            import sys
            sys.path.append(path)
            import _all_test_c
            _all_test_c.find_and_load_library = func
        """)


all_names = ', '.join(Module.interpleveldefs.keys())

lst = []
for name, value in _backend_test_c.__dict__.items():
    if name.startswith('test_'):
        lst.append(value)
lst.sort(key=lambda func: func.func_code.co_firstlineno)

tmpdir = udir.join('test_c').ensure(dir=1)

tmpname = tmpdir.join('_test_c.py')
with tmpname.open('w') as f:
    for func in lst:
        print >> f, 'def %s(self):' % (func.__name__,)
        print >> f, '    import _all_test_c'
        print >> f, '    _all_test_c.%s()' % (func.__name__,)

tmpname2 = tmpdir.join('_all_test_c.py')
with tmpname2.open('w') as f:
    print >> f, 'import sys'
    print >> f, 'from _ffi_backend import %s' % all_names
    print >> f, 'class py:'
    print >> f, '    class test:'
    print >> f, '        raises = staticmethod(raises)'
    print >> f, py.path.local(__file__).join('..', '_backend_test_c.py').read()


mod = tmpname.pyimport()
for key, value in mod.__dict__.items():
    if key.startswith('test_'):
        setattr(AppTestC, key, value)
