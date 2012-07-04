from __future__ import with_statement
"""
This file is OBSCURE.  Really.  The purpose is to avoid copying and changing
'test_c.py' from cffi/c/.
"""
import py, ctypes
from pypy.tool.udir import udir
from pypy.conftest import gettestobjspace
from pypy.interpreter import gateway
from pypy.module._cffi_backend.test import _backend_test_c
from pypy.module._cffi_backend import Module
from pypy.translator.platform import host
from pypy.translator.tool.cbuild import ExternalCompilationInfo


class AppTestC(object):
    """Populated below, hack hack hack."""

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_cffi_backend',))
        cls.space = space
        testfuncs_w = []
        keepalive_funcs = []

        def find_and_load_library_for_test(space, w_name):
            import ctypes.util
            path = ctypes.util.find_library(space.str_w(w_name))
            return space.appexec([space.wrap(path)], """(path):
                import _cffi_backend
                return _cffi_backend.load_library(path)""")

        test_lib_c = tmpdir.join('_test_lib.c')
        src_test_lib_c = py.path.local(__file__).dirpath().join('_test_lib.c')
        src_test_lib_c.copy(test_lib_c)
        eci = ExternalCompilationInfo()
        test_lib = host.compile([test_lib_c], eci, standalone=False)

        cdll = ctypes.CDLL(str(test_lib))
        cdll.gettestfunc.restype = ctypes.c_void_p

        def testfunc_for_test(space, w_num):
            addr = cdll.gettestfunc(space.int_w(w_num))
            return space.wrap(addr)

        w_func = space.wrap(gateway.interp2app(find_and_load_library_for_test))
        w_testfunc = space.wrap(gateway.interp2app(testfunc_for_test))
        space.appexec([space.wrap(str(tmpdir)), w_func, w_testfunc],
        """(path, func, testfunc):
            import sys
            sys.path.append(path)
            import _all_test_c
            _all_test_c.find_and_load_library = func
            _all_test_c._testfunc = testfunc
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
    print >> f, 'from _cffi_backend import %s' % all_names
    print >> f, 'class py:'
    print >> f, '    class test:'
    print >> f, '        raises = staticmethod(raises)'
    print >> f, py.path.local(__file__).join('..', '_backend_test_c.py').read()


mod = tmpname.pyimport()
for key, value in mod.__dict__.items():
    if key.startswith('test_'):
        setattr(AppTestC, key, value)
