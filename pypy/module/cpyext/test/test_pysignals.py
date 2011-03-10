from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestBufferObject(AppTestCpythonExtensionBase):
    def test_signals(self):
        module = self.import_extension('foo', [
            ("test_signals", "METH_NOARGS",
             """
                 PyOS_sighandler_t handler = SIG_IGN;
                 PyOS_sighandler_t oldhandler;
                 int result = 0;
                 
                 oldhandler = PyOS_getsig(SIGUSR1);
                 
                 handler = PyOS_setsig(SIGUSR1, SIG_IGN);
                 
                 if( oldhandler != handler )
                     result += 1;
                 
                 handler = PyOS_setsig(SIGUSR1, oldhandler);
                 
                 if( handler != SIG_IGN )
                     result += 2;
                 
                 return PyInt_FromLong(result);
             """),
            ], prologue = """
            #include <signal.h>
            """)
        res = module.test_signals()
        assert res == 0
