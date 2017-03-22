from pypy.module.cpyext.modsupport import PyModule_New
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi


class TestModuleObject(BaseApiTest):
    def test_module_new(self, space):
        with rffi.scoped_str2charp('testname') as buf:
            w_mod = PyModule_New(space, buf)
        assert space.eq_w(space.getattr(w_mod, space.newtext('__name__')),
                          space.newtext('testname'))

    def test_module_getname(self, space, api):
        w_sys = space.wrap(space.sys)
        p = api.PyModule_GetName(w_sys)
        assert rffi.charp2str(p) == 'sys'
        p2 = api.PyModule_GetName(w_sys)
        assert p2 == p
        self.raises(space, api, SystemError, api.PyModule_GetName, space.w_True)


class AppTestModuleObject(AppTestCpythonExtensionBase):
    def test_getdef(self):
        module = self.import_extension('foo', [
            ("check_getdef_same", "METH_NOARGS",
             """
                 return PyBool_FromLong(PyModule_GetDef(mod_global) == &moduledef);
             """
            )], prologue="""
            static struct PyModuleDef moduledef;
            static PyObject *mod_global;
            """, more_init="""
               mod_global = mod;
            """)
        assert module.check_getdef_same()
