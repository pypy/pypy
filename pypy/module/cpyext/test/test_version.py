from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestVersion(AppTestCpythonExtensionBase):

    def test_versions(self):
        import sys
        init = """
        if (Py_IsInitialized()) {
            PyObject *m = Py_InitModule("foo", NULL);
            PyModule_AddStringConstant(m, "py_version", PY_VERSION);
            PyModule_AddIntConstant(m, "py_major_version", PY_MAJOR_VERSION);
            PyModule_AddIntConstant(m, "py_minor_version", PY_MINOR_VERSION);
            PyModule_AddIntConstant(m, "py_micro_version", PY_MICRO_VERSION);
            PyModule_AddStringConstant(m, "pypy_version", PYPY_VERSION);
        }
        """
        module = self.import_module(name='foo', init=init)
        assert module.py_version == sys.version[:5]
        assert module.py_major_version == sys.version_info.major
        assert module.py_minor_version == sys.version_info.minor
        assert module.py_micro_version == sys.version_info.micro
        v = sys.pypy_version_info
        s = '%d.%d.%d' % (v[0], v[1], v[2])
        if v.releaselevel != 'final':
            s += '-%s%d' % (v[3], v[4])
        assert module.pypy_version == s
