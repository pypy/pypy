from __future__ import with_statement
"""
This file is OBSCURE.  Really.  The purpose is to avoid copying and changing
'test_c.py' from cffi/c/ in the original CFFI repository:
    https://bitbucket.org/cffi/cffi

Adding a test here involves:
1. add a test to cffi/c/test.py
   - if you need a C function to call, add it into _cffi_backend.c
     as a testfuncNN().
2. have it pass when you run 'py.test test_c.py' in cffi
3. check in and (if you can) push the changes
4. copy test_c.py into _backend_test.py here, killing the few lines of header
   - if you added a C function, it goes into _test_lib.c here
   - if you could complete step 3, try running 'py.test test_file.py' here
5. make the test pass in pypy ('py.test test_c.py')
"""
import py, sys, ctypes
if sys.version_info < (2, 6):
    py.test.skip("requires the b'' literal syntax")

from rpython.tool.udir import udir
from pypy.interpreter import gateway
from pypy.module._cffi_backend import Module
from pypy.module._cffi_backend.newtype import _clean_cache, UniqueCache
from rpython.translator import cdir
from rpython.translator.platform import host
from rpython.translator.tool.cbuild import ExternalCompilationInfo


class AppTestC(object):
    """Populated below, hack hack hack."""

    spaceconfig = dict(usemodules=('_cffi_backend', 'cStringIO', 'array'))

    def setup_class(cls):
        testfuncs_w = []
        keepalive_funcs = []
        UniqueCache.for_testing = True

        def find_and_load_library_for_test(space, w_name, w_is_global=None):
            if w_is_global is None:
                w_is_global = space.wrap(0)
            if space.is_w(w_name, space.w_None):
                path = None
            else:
                import ctypes.util
                path = ctypes.util.find_library(space.str_w(w_name))
            return space.appexec([space.wrap(path), w_is_global],
            """(path, is_global):
                import _cffi_backend
                return _cffi_backend.load_library(path, is_global)""")

        test_lib_c = tmpdir.join('_test_lib.c')
        src_test_lib_c = py.path.local(__file__).dirpath().join('_test_lib.c')
        src_test_lib_c.copy(test_lib_c)
        eci = ExternalCompilationInfo(include_dirs=[cdir])
        test_lib = host.compile([test_lib_c], eci, standalone=False)

        cdll = ctypes.CDLL(str(test_lib))
        cdll.gettestfunc.restype = ctypes.c_void_p

        def testfunc_for_test(space, w_num):
            if hasattr(space, 'int_w'):
                w_num = space.int_w(w_num)
            addr = cdll.gettestfunc(w_num)
            return space.wrap(addr)

        space = cls.space
        if cls.runappdirect:
            def interp2app(func):
                def run(*args):
                    return func(space, *args)
                return run
        else:
            interp2app = gateway.interp2app

        w_func = space.wrap(interp2app(find_and_load_library_for_test))
        w_testfunc = space.wrap(interp2app(testfunc_for_test))
        space.appexec([space.wrap(str(tmpdir)), w_func, w_testfunc,
                       space.wrap(sys.version[:3])],
        """(path, func, testfunc, underlying_version):
            import sys
            sys.path.append(path)
            import _all_test_c
            _all_test_c.PY_DOT_PY = underlying_version
            _all_test_c.find_and_load_library = func
            _all_test_c._testfunc = testfunc
        """)

    def teardown_method(self, method):
        _clean_cache(self.space)

    def teardown_class(cls):
        UniqueCache.for_testing = False


all_names = ', '.join(Module.interpleveldefs.keys())

backend_test_c = py.path.local(__file__).join('..', '_backend_test_c.py')

lst = []
with backend_test_c.open('r') as f:
    for line in f:
        if line.startswith('def test_'):
            line = line[4:]
            line = line[:line.index('():')]
            lst.append(line)

tmpdir = udir.join('test_c').ensure(dir=1)

tmpname = tmpdir.join('_test_c.py')
with tmpname.open('w') as f:
    for func in lst:
        print >> f, 'def %s(self):' % (func,)
        print >> f, '    import _all_test_c'
        print >> f, '    _all_test_c.%s()' % (func,)

tmpname2 = tmpdir.join('_all_test_c.py')
with tmpname2.open('w') as f:
    print >> f, 'import sys'
    print >> f, 'from _cffi_backend import %s' % all_names
    print >> f, 'class py:'
    print >> f, '    class test:'
    print >> f, '        raises = staticmethod(raises)'
    print >> f, '        skip = staticmethod(skip)'
    print >> f, backend_test_c.read()


mod = tmpname.pyimport()
for key, value in mod.__dict__.items():
    if key.startswith('test_'):
        setattr(AppTestC, key, value)
