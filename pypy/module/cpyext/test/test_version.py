from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestVersion(AppTestCpythonExtensionBase):

    def test_versions(self):
        import sys
        init = """
        if (Py_IsInitialized()) {
            PyObject *m = Py_InitModule("foo", NULL);
            PyModule_AddStringConstant(m, "py_version", PY_VERSION);
            PyModule_AddStringConstant(m, "pypy_version", PYPY_VERSION);
        }
        """
        module = self.import_module(name='foo', init=init)
        assert module.py_version == sys.version[:5]
        assert module.pypy_version == '%d.%d.%d' % sys.pypy_version_info[:3]
