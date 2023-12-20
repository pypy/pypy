from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestCapsule(AppTestCpythonExtensionBase):
    def test_capsule_import(self):
        module = self.import_extension('foo', [
            ("set_ptr", "METH_O",
             """
                 PyObject *capsule, *module;
                 void *ptr = PyLong_AsVoidPtr(args);
                 if (PyErr_Occurred()) return NULL;
                 capsule = PyCapsule_New(ptr, "foo._ptr", NULL);
                 if (PyErr_Occurred()) return NULL;
                 module = PyImport_ImportModule("foo");
                 PyModule_AddObject(module, "_ptr", capsule);
                 Py_DECREF(module);
                 if (PyErr_Occurred()) return NULL;
                 Py_RETURN_NONE;
             """),
            ("get_ptr", "METH_NOARGS",
             """
                 void *ptr = PyCapsule_Import("foo._ptr", 0);
                 if (PyErr_Occurred()) return NULL;
                 return PyLong_FromVoidPtr(ptr);
             """)])
        module.set_ptr(1234)
        assert 'capsule object "foo._ptr" at ' in str(module._ptr)
        import gc; gc.collect()
        assert module.get_ptr() == 1234
        del module._ptr

    def test_capsule_set(self):
        # taken from _testcapimodule.c
        module = self.import_extension('foo', [
            ("test_capsule", "METH_NOARGS",
            """
            PyObject *object;
            const char *error = NULL;
            char *known = "known";
            PyObject *gc_module = PyImport_ImportModule("gc");
            PyObject *collect = PyObject_GetAttrString(gc_module, "collect");
        #define FAIL(x) { error = (x); goto exit; }

        #define CHECK_DESTRUCTOR                        \\
            PyObject_CallFunction(collect, NULL);       \\
            PyObject_CallFunction(collect, NULL);       \\
            PyObject_CallFunction(collect, NULL);       \\
            if (capsule_error) {                        \\
                FAIL(capsule_error);                    \\
            }                                           \\
            else if (!capsule_destructor_call_count) {  \\
                FAIL("destructor not called!");         \\
            }                                           \\
            capsule_destructor_call_count = 0;

            object = PyCapsule_New(capsule_pointer, capsule_name, capsule_destructor);
            PyCapsule_SetContext(object, capsule_context);
            capsule_destructor(object);
            CHECK_DESTRUCTOR;
            Py_DECREF(object);
            CHECK_DESTRUCTOR;

            object = PyCapsule_New(known, "ignored", NULL);
            PyCapsule_SetPointer(object, capsule_pointer);
            PyCapsule_SetName(object, capsule_name);
            PyCapsule_SetDestructor(object, capsule_destructor);
            PyCapsule_SetContext(object, capsule_context);
            capsule_destructor(object);
            CHECK_DESTRUCTOR;
            /* intentionally access using the wrong name */
            void *pointer2 = PyCapsule_GetPointer(object, "the wrong name");
            if (!PyErr_Occurred()) {
                FAIL("PyCapsule_GetPointer should have failed but did not!");
            }
            PyErr_Clear();
            if (pointer2) {
                if (pointer2 == capsule_pointer) {
                    FAIL("PyCapsule_GetPointer should not have"
                             " returned the internal pointer!");
                } else {
                    FAIL("PyCapsule_GetPointer should have "
                             "returned NULL pointer but did not!");
                }
            }
            PyCapsule_SetDestructor(object, NULL);
            Py_DECREF(object);
            if (capsule_destructor_call_count) {
                FAIL("destructor called when it should not have been!");
            }

          exit:
            Py_DECREF(gc_module);
            Py_DECREF(collect);
            if (error) {
                PyErr_Format(PyExc_RuntimeError, "test_capsule: %s", error);
                return NULL;
            }
            Py_RETURN_NONE;
        #undef FAIL

            """),
            ], prologue="""
                #include <Python.h>
                /* Coverage testing of capsule objects. */

                static const char *capsule_name = "capsule name";
                static       char *capsule_pointer = "capsule pointer";
                static       char *capsule_context = "capsule context";
                static const char *capsule_error = NULL;
                static int
                capsule_destructor_call_count = 0;

                static void
                capsule_destructor(PyObject *o) {
                    capsule_destructor_call_count++;
                    if (PyCapsule_GetContext(o) != capsule_context) {
                        capsule_error = "context did not match in destructor!";
                    } else if (PyCapsule_GetDestructor(o) != capsule_destructor) {
                        capsule_error = "destructor did not match in destructor!  (woah!)";
                    } else if (PyCapsule_GetName(o) != capsule_name) {
                        capsule_error = "name did not match in destructor!";
                    } else if (PyCapsule_GetPointer(o, capsule_name) != capsule_pointer) {
                        capsule_error = "pointer did not match in destructor!";
                    }
                }
                """
                )
        import gc
        # make the calls to `collect` in C reach the `debug_collect` mock function
        _collect = gc.collect
        gc.collect = self.debug_collect
        try:
            module.test_capsule()
        finally:
            gc.collect = _collect
