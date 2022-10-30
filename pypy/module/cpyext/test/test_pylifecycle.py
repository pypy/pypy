from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestLifeCycleObject(AppTestCpythonExtensionBase):

    def spawn(self, *args, **kwds):
        try:
            import pexpect
        except ImportError as e:
            py.test.skip(str(e))
        kwds.setdefault('timeout', 10)
        print('SPAWN:', ' '.join([args[0]] + args[1]), kwds)
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def test_Py_Initialize(self):
        from time import strftime

        exe = self.build_exe("foo",
            """
                wchar_t *program = Py_DecodeLocale(argv[0], NULL);
                if (program == NULL) {
                    fprintf(stderr, "Fatal error: cannot decode argv[0]\n");
                    exit(1);
                }
                Py_SetProgramName(program);  /* optional but recommended */
                Py_Initialize();
                PyRun_SimpleString("from time import strftime\n"
                                   "print('Today is', strftime('%Y %b %d'))\n");
                if (Py_FinalizeEx() < 0) {
                    exit(120);
                }
                PyMem_RawFree(program);
            """, PY_SSIZE_T_CLEAN=True,
            )
        child = self.spawn(exe)
        child.expect("Today is %s" % strftime('%Y %b %d'))
