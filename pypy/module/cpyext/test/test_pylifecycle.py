from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestLifeCycleObject(AppTestCpythonExtensionBase):
    def test_Py_Initialize(self):
        from time import strftime
        import io, sys

        module = self.import_extension("foo", [
            ("initialize", "METH_NOARGS",
            """
                // Py_SetProgramName("test_initialize");  /* optional but recommended */
                Py_Initialize();
                if (PyErr_Occurred())
                    return NULL;
                PyRun_SimpleString("from time import strftime\\n"
                                   "print('Today is', strftime('%Y %b %d'))\\n");
                /* if (Py_FinalizeEx() < 0) {
                    exit(120);
                } */
                Py_RETURN_TRUE;
            """),
            ])
        old = sys.stdout 
        sys.stdout = io.StringIO()
        try:
            assert module.initialize()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = sys.__stdout__
