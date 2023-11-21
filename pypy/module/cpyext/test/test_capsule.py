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
            known_capsule known_capsules[] = {
                #define KNOWN_CAPSULE(module, name)             { module "." name, module, name }
                KNOWN_CAPSULE("_socket", "CAPI"),
                KNOWN_CAPSULE("_curses", "_C_API"),
                // KNOWN_CAPSULE("datetime", "datetime_CAPI"),
                { NULL, NULL },
            };
            known_capsule *known = &known_capsules[0];

            PyObject *gc_module = PyImport_ImportModule("gc");
            PyObject *collect = PyObject_GetAttrString(gc_module, "collect");
        #define FAIL(x) { error = (x); goto exit; }

        #define CHECK_DESTRUCTOR                        \\
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

            for (known = &known_capsules[0]; known->module != NULL; known++) {
                /* yeah, ordinarily I wouldn't do this either,
                   but it's fine for this test harness.
                */
                static char buffer[256];
        #undef FAIL
        #define FAIL(x) \\
                { \\
                sprintf(buffer, "%s module: \\"%s\\" attribute: \\"%s\\"", \\
                    x, known->module, known->attribute); \\
                error = buffer; \\
                goto exit; \\
                }

                PyObject *module = PyImport_ImportModule(known->module);
                if (module) {
                    void *pointer = PyCapsule_Import(known->name, 0);
                    if (!pointer) {
                        Py_DECREF(module);
                        FAIL("PyCapsule_GetPointer returned NULL unexpectedly!");
                    }
                    object = PyObject_GetAttrString(module, known->attribute);
                    if (!object) {
                        Py_DECREF(module);
                        return NULL;
                    }
                    pointer2 = PyCapsule_GetPointer(object,
                                            "weebles wobble but they don't fall down");
                    if (!PyErr_Occurred()) {
                        Py_DECREF(object);
                        Py_DECREF(module);
                        FAIL("PyCapsule_GetPointer should have failed but did not!");
                    }
                    PyErr_Clear();
                    if (pointer2) {
                        Py_DECREF(module);
                        Py_DECREF(object);
                        if (pointer2 == pointer) {
                            FAIL("PyCapsule_GetPointer should not have"
                                     " returned its internal pointer!");
                        } else {
                            FAIL("PyCapsule_GetPointer should have"
                                     " returned NULL pointer but did not!");
                        }
                    }
                    Py_DECREF(object);
                    Py_DECREF(module);
                }
                else
                    PyErr_Clear();
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
                #include <stdio.h>
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

                typedef struct {
                    char *name;
                    char *module;
                    char *attribute;
                } known_capsule;
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
