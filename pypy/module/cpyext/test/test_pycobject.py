from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestStringObject(AppTestCpythonExtensionBase):
    def test_pycobject_import(self):
        module = self.import_extension('foo', [
            ("set_ptr", "METH_O",
             """
                 PyObject *pointer, *module;
                 void *ptr = PyLong_AsVoidPtr(args);
                 if (PyErr_Occurred()) return NULL;
                 pointer = PyCObject_FromVoidPtr(ptr, NULL);
                 if (PyErr_Occurred()) return NULL;
                 module = PyImport_ImportModule("foo");
                 PyModule_AddObject(module, "_ptr", pointer);
                 Py_DECREF(pointer);  /* XXX <--- anti-workaround */
                 Py_DECREF(module);
                 if (PyErr_Occurred()) return NULL;
                 Py_RETURN_NONE;
             """),
            ("get_ptr", "METH_NOARGS",
             """
                 void *ptr = PyCObject_Import("foo", "_ptr");
                 if (PyErr_Occurred()) return NULL;
                 return PyLong_FromVoidPtr(ptr);
             """)])
        module.set_ptr(1234)
        assert "PyCObject object" in str(module._ptr)
        import gc; gc.collect()
        assert module.get_ptr() == 1234
        del module._ptr
