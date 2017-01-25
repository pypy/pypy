from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestMmap(AppTestCpythonExtensionBase):
    def test_mmap_buffer(self):
        module = self.import_extension('mmap_buffer', [
            ('isbuffer', 'METH_O',
             """
             Py_buffer view;

             if (PyObject_GetBuffer(args, &view,
                    PyBUF_ANY_CONTIGUOUS|PyBUF_WRITABLE) != 0) {
                return NULL;
             }
             return PyLong_FromLong(1);
             """)])
        import os, mmap
        tmpname = os.path.join(self.udir, 'test_mmap_buffer')
        print(tmpname)
        with open(tmpname, 'w+b') as f:
            f.write(b'123')
            f.flush()
            m = mmap.mmap(f.fileno(), 3)
            assert module.isbuffer(m) == 1
