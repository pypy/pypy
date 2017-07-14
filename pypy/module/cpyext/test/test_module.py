import pytest
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.modsupport import PyModule_New, PyModule_GetName
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi


class TestModuleObject(BaseApiTest):
    def test_module_new(self, space):
        with rffi.scoped_str2charp('testname') as buf:
            w_mod = PyModule_New(space, buf)
        assert space.eq_w(space.getattr(w_mod, space.newtext('__name__')),
                          space.newtext('testname'))

    def test_module_getname(self, space):
        w_sys = space.wrap(space.sys)
        p = PyModule_GetName(space, w_sys)
        assert rffi.charp2str(p) == 'sys'
        p2 = PyModule_GetName(space, w_sys)
        assert p2 == p
        with pytest.raises(OperationError) as excinfo:
            PyModule_GetName(space, space.w_True)
        assert excinfo.value.w_type is space.w_SystemError


class AppTestModuleObject(AppTestCpythonExtensionBase):
    def test_getdef(self):
        module = self.import_extension('foo', [
            ("check_getdef_same", "METH_NOARGS",
             """
                 return PyBool_FromLong(PyModule_GetDef(self) == &moduledef);
             """
            )], prologue="""
            static struct PyModuleDef moduledef;
            """)
        assert module.check_getdef_same()

    def test_getstate(self):
        module = self.import_extension('foo', [
            ("check_mod_getstate", "METH_NOARGS",
             """
                 struct module_state { int foo[51200]; };
                 static struct PyModuleDef moduledef = {
                     PyModuleDef_HEAD_INIT,
                     "module_getstate_myextension",
                     NULL,
                     sizeof(struct module_state)
                 };
                 PyObject *module = PyModule_Create(&moduledef);
                 int *p = (int *)PyModule_GetState(module);
                 int i;
                 for (i = 0; i < 51200; i++)
                     if (p[i] != 0)
                         return PyBool_FromLong(0);
                 Py_DECREF(module);
                 return PyBool_FromLong(1);
             """
            )])
        assert module.check_mod_getstate()


class AppTestMultiPhase(AppTestCpythonExtensionBase):
    def test_basic(self):
        from types import ModuleType
        module = self.import_module(name='multiphase')
        assert isinstance(module, ModuleType)
        assert module.__name__ == 'multiphase'
        assert module.__doc__ == "example docstring"

    def test_getdef(self):
        from types import ModuleType
        module = self.import_module(name='multiphase')
        assert module.check_getdef_same()

    def test_slots(self):
        from types import ModuleType
        body = """
        static PyModuleDef multiphase_def;

        static PyObject* multiphase_create(PyObject *spec, PyModuleDef *def) {
            PyObject *module = PyModule_New("altname");
            PyObject_SetAttrString(module, "create_spec", spec);
            PyObject_SetAttrString(module, "create_def_eq",
                                   PyBool_FromLong(def == &multiphase_def));
            return module;
        }

        static int multiphase_exec(PyObject* module) {
            Py_INCREF(Py_True);
            PyObject_SetAttrString(module, "exec_called", Py_True);
            return 0;
        }

        static PyModuleDef_Slot multiphase_slots[] = {
            {Py_mod_create, multiphase_create},
            {Py_mod_exec, multiphase_exec},
            {0, NULL}
        };

        static PyModuleDef multiphase_def = {
            PyModuleDef_HEAD_INIT,                      /* m_base */
            "multiphase",                               /* m_name */
            "example docstring",                        /* m_doc */
            0,                                          /* m_size */
            NULL,                                       /* m_methods */
            multiphase_slots,                           /* m_slots */
            NULL,                                       /* m_traverse */
            NULL,                                       /* m_clear */
            NULL,                                       /* m_free */
        };
        """
        init = """
        return PyModuleDef_Init(&multiphase_def);
        """
        module = self.import_module(name='multiphase', body=body, init=init)
        assert module.create_spec
        assert module.create_spec is module.__spec__
        assert module.create_def_eq
        assert module.exec_called

    def test_forget_init(self):
        from types import ModuleType
        body = """
        static PyModuleDef multiphase_def = {
            PyModuleDef_HEAD_INIT,                      /* m_base */
            "multiphase",                               /* m_name */
            "example docstring",                        /* m_doc */
            0,                                          /* m_size */
        };
        """
        init = """
        return (PyObject *) &multiphase_def;
        """
        raises(SystemError, self.import_module, name='multiphase', body=body,
               init=init)
