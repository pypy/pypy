from pypy.conftest import gettestobjspace
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator import platform
from pypy.module.cpyext import api
from test_cpyext import compile_module

import py, autopath
import sys

class AppTestFloatObject:
    def setup_class(cls):
        cls.api_library = api.build_bridge(cls.space, rename=True)

    def setup_method(self, func):
        self.w_import_module = self.space.wrap(self.import_module)

    def teardown_method(self, func):
        try:
            self.space.delitem(self.space.sys.get('modules'),
                               self.space.wrap('foo'))
        except OperationError:
            pass

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

    def test_floatobject(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        PyObject* foo_FromDouble(PyObject* self, PyObject *args)
        {
            return PyFloat_FromDouble(3.14);
        }
        double foo_AsDouble(PyObject* self, PyObject *args)
        {
            PyObject* pi = PyFloat_FromDouble(3.14);
            return PyFloat_AsDouble(pi);
        }
        static PyMethodDef methods[] = {
            { "FromDouble", foo_FromDouble, METH_NOARGS },
            { "AsDouble", foo_AsDouble, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert module.FromDouble() == 3.14
        assert module.AsDouble() == 3.14
