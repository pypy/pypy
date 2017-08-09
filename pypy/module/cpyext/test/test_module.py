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

    def test_multiphase2(self):
        import sys
        from importlib import machinery, util
        NAME = 'multiphase2'
        module = self.import_module(name=NAME)
        finder = machinery.FileFinder(None)
        spec = util.find_spec(NAME)
        assert spec
        assert module.__name__ == NAME
        #assert module.__file__ == spec.origin
        assert module.__package__ == ''
        raises(AttributeError, 'module.__path__')
        assert module is sys.modules[NAME]
        assert isinstance(module.__loader__, machinery.ExtensionFileLoader)

    def test_functionality(self):
        import types
        NAME = 'multiphase2'
        module = self.import_module(name=NAME)
        assert isinstance(module, types.ModuleType)
        ex = module.Example()
        assert ex.demo('abcd') == 'abcd'
        assert ex.demo() is None
        raises(AttributeError, 'ex.abc')
        ex.abc = 0
        assert ex.abc == 0
        assert module.foo(9, 9) == 18
        assert isinstance(module.Str(), str)
        assert module.Str(1) + '23' == '123'
        raises(module.error, 'raise module.error()')
        assert module.int_const == 1969
        assert module.str_const == 'something different'

    def test_reload(self):
        import importlib
        NAME = 'multiphase2'
        module = self.import_module(name=NAME)
        ex_class = module.Example
        importlib.reload(module)
        assert ex_class is module.Example

    def w_load_from_spec(self, loader, spec):
        from importlib import util
        module = util.module_from_spec(spec)
        loader.exec_module(module)
        return module

    def test_bad_modules(self):
        # XXX: not a very good test, since most internal issues in cpyext
        # cause SystemErrors.
        from importlib import machinery, util
        NAME = 'multiphase2'
        module = self.import_module(name=NAME)
        origin = module.__loader__.path
        for name_base in [
                'bad_slot_large',
                'bad_slot_negative',
                'create_int_with_state',
                'negative_size',
                'export_null',
                'export_uninitialized',
                'export_raise',
                'export_unreported_exception',
                'create_null',
                'create_raise',
                'create_unreported_exception',
                'nonmodule_with_exec_slots',
                'exec_err',
                'exec_raise',
                'exec_unreported_exception',
                ]:
            name = '_testmultiphase_' + name_base
            loader = machinery.ExtensionFileLoader(name, origin)
            spec = util.spec_from_loader(name, loader)
            raises(SystemError, self.load_from_spec, loader, spec)
