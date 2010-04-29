from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestThreads(AppTestCpythonExtensionBase):
    def test_allow_threads(self):
        module = self.import_extension('foo', [
            ("test", "METH_NOARGS",
             """
                Py_BEGIN_ALLOW_THREADS
                {
                    Py_BLOCK_THREADS
                    Py_UNBLOCK_THREADS
                }
                Py_END_ALLOW_THREADS
                Py_RETURN_NONE;
             """),
            ])
        # Should compile at least
        module.test()

