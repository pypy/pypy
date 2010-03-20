from pypy.conftest import gettestobjspace
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator import platform
from pypy.module.cpyext import api

import py, autopath
import sys

class TestApi():
    def test_signature(self):
        assert 'Py_InitModule' in api.FUNCTIONS
        assert api.FUNCTIONS['Py_InitModule'].argtypes == [
            rffi.CCHARP, lltype.Ptr(api.TYPES['PyMethodDef'])]
        assert api.FUNCTIONS['Py_InitModule'].restype == lltype.Void

def compile_module(modname, code, **kwds):
    eci = ExternalCompilationInfo(
        separate_module_sources=[code],
        export_symbols=['init%s' % (modname,)],
        include_dirs=api.include_dirs,
        **kwds
        )
    eci = eci.convert_sources_to_files()
    soname = platform.platform.compile(
        [], eci,
        standalone=False)
    return str(soname)

class AppTestCpythonExtension:
    def setup_class(cls):
        cls.api_library = api.build_bridge(cls.space, rename=True)

    def import_module(self, name, init, body=''):
        code = """
        #include <pypy_rename.h>
        #include <Python.h>
        %(body)s

        void init%(name)s(void) {
        %(init)s
        }
        """ % dict(name=name, init=init, body=body)
        if sys.platform == 'win32':
            libraries = [self.api_library]
            mod = compile_module(name, code, libraries=libraries)
        else:
            libraries = [str(self.api_library+'.so')]
            mod = compile_module(name, code, link_files=libraries)
        import ctypes
        initfunc = ctypes.CDLL(mod)['init%s' % (name,)]
        initfunc()
        return self.space.getitem(
            self.space.sys.get('modules'),
            self.space.wrap(name))

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

    def test_export_function(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        PyObject* foo_pi(PyObject* self, PyObject *args)
        {
            return PyFloat_FromDouble(3.14);
        }
        static PyMethodDef methods[] = {
            { "return_pi", foo_pi, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert 'return_pi' in dir(module)
        assert module.return_pi is not None
        assert module.return_pi() is None # XXX for the moment
