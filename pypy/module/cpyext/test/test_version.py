import sys

import py, pytest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


def test_pragma_version():
    from pypy.module.sys.version import CPYTHON_VERSION
    rootdir = py.path.local(__file__).join('..', '..')
    pyconfig_h = rootdir.join('include', 'pyconfig.h')
    version = '%d%d' % (CPYTHON_VERSION[0], CPYTHON_VERSION[1])
    pragma = 'pragma comment(lib,"python%s.lib")' % version
    assert pragma in pyconfig_h.read()


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
        }
        """
        module = self.import_module(name='foo', init=init)
        assert module.py_version == '%d.%d.%d' % sys.version_info[:3]
        assert module.py_major_version == sys.version_info.major
        assert module.py_minor_version == sys.version_info.minor
        assert module.py_micro_version == sys.version_info.micro

    #@pytest.mark.skipif('__pypy__' not in sys.builtin_module_names, reason='pypy only test')
    def test_pypy_versions(self):
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            py.test.skip("pypy only test")
        init = """
        if (Py_IsInitialized()) {
            PyObject *m = Py_InitModule("foo", NULL);
            PyModule_AddStringConstant(m, "pypy_version", PYPY_VERSION);
            PyModule_AddIntConstant(m, "pypy_version_num", PYPY_VERSION_NUM);
        }
        """
        module = self.import_module(name='foo', init=init)
        v = sys.pypy_version_info
        s = '%d.%d.%d' % (v[0], v[1], v[2])
        if v.releaselevel != 'final':
            s += '-%s%d' % (v[3], v[4])
        assert module.pypy_version == s
        assert module.pypy_version_num == ((v[0] << 24) |
                                           (v[1] << 16) |
                                           (v[2] << 8))
