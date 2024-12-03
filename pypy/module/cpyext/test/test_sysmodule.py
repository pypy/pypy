from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi

class AppTestSysModule(AppTestCpythonExtensionBase):
    def test_sysmodule(self):
        module = self.import_extension('foo', [
            ("get", "METH_VARARGS",
             """
                 char *name = _PyUnicode_AsString(PyTuple_GetItem(args, 0));
                 PyObject *retval = PySys_GetObject(name);
                 return PyBool_FromLong(retval != NULL);
             """)])
        assert module.get("excepthook")
        assert not module.get("spam_spam_spam")

    def test_writestdout(self):
        module = self.import_extension('foo', [
            ("writestdout", "METH_NOARGS",
             """
                 PySys_WriteStdout("format: %d\\n", 42);
                 Py_RETURN_NONE;
             """)])
        import sys, io
        prev = sys.stdout
        sys.stdout = io.StringIO()
        try:
            module.writestdout()
            assert sys.stdout.getvalue() == "format: 42\n"
        finally:
            sys.stdout = prev

    def test_sysgetset(self):
        module = self.import_extension('foo', [
            ("setobject", "METH_VARARGS",
             """
                const char *name;
                Py_ssize_t size;
                PyObject *value = NULL;
                if (!PyArg_ParseTuple(args, "z#|O", &name, &size, &value)) {
                    return NULL;
                }
                if (value == Py_None) {
                    value = NULL;
                }
                int ret = PySys_SetObject(name, value);
                if (ret < 0)
                    return NULL;
                return PyLong_FromLong(ret);
             """)], PY_SSIZE_T_CLEAN=True)
        import sys
        module.setobject("newattr", 1)
        assert sys.newattr == 1
        module.setobject("newattr")
        assert not hasattr(sys, 'newattr')
        # Cpython lets you call this, even if the attribute does not exist
        module.setobject("newattr")
        with raises(UnicodeDecodeError):
            module.setobject(b'\xff', 1)
