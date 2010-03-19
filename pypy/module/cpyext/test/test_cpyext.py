import py, autopath

from pypy.conftest import gettestobjspace
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator import platform
from pypy.module.cpyext import api

class TestApi():
    def test_signature(self):
        assert 'Py_InitModule' in api.FUNCTIONS
        assert api.FUNCTIONS['Py_InitModule'].argtypes == [
            rffi.CCHARP, lltype.Ptr(api.TYPES['PyMethodDef'])]
        assert api.FUNCTIONS['Py_InitModule'].restype == lltype.Void

def compile_module(name, code, libraries=()):
    include_dir = py.path.local(autopath.pypydir).join(
        'module', 'cpyext', 'include')
    eci = ExternalCompilationInfo(
        separate_module_sources=[code],
        export_symbols=['init%s' % (name,)],
        include_dirs=[include_dir],
        libraries=libraries,
        )
    eci = eci.convert_sources_to_files()
    soname = platform.platform.compile(
        [], eci,
        standalone=False)
    return str(soname)

class AppTestCpythonExtension:
    def setup_class(cls):
        cls.api_library = api.build_bridge(cls.space)

    def import_module(self, name, init, body=''):
        code = """
        #include <Python.h>
        %(body)s

        void init%(name)s(void) {
        %(init)s
        }
        """ % dict(name=name, init=init, body=body)
        mod = compile_module(name, code, libraries=[self.api_library])
        import ctypes
        initfunc = ctypes.CDLL(mod)['init%s' % (name,)]
        initfunc()

    def setup_method(self, func):
        self.w_import_module = self.space.wrap(self.import_module)

    def teardown_method(self, func):
        try:
            self.space.delitem(self.space.sys.get('modules'),
                               self.space.wrap('foo'))
        except OperationError:
            pass

    def test_createmodule(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", NULL);
        """
        self.import_module(name='foo', init=init)
        assert 'foo' in sys.modules
