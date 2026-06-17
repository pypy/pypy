from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestBuffer(AppTestCpythonExtensionBase):
    def test_AsWriteBuffer(self):
        import array
        module = self.import_extension('buffer', [
            ('write_buffer_len', 'METH_O',
             """
             void* buf;
             Py_ssize_t buf_len;
             if (PyObject_AsWriteBuffer(args, &buf, &buf_len) < 0) {
                //PyErr_SetString(PyExc_ValueError, "bad value");
                return NULL;
             }
             return PyLong_FromLong(buf_len);
             """)])
        assert module.write_buffer_len(bytearray(b'123')) == 3
        assert module.write_buffer_len(array.array('i', [1, 2, 3])) == 12
        #
        import _cffi_backend
        BChar = _cffi_backend.new_primitive_type("char")
        BCharPtr = _cffi_backend.new_pointer_type(BChar)
        BCharArray = _cffi_backend.new_array_type(BCharPtr, None)
        p = _cffi_backend.newp(BCharArray, b"abcde")
        bb = _cffi_backend.buffer(p)
        assert module.write_buffer_len(bb) == 6

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

    def test_applevel(self):
        module = self.import_extension("foo", [
            ("getbuffer", "METH_O", """
            Py_buffer view;
            if (!PyObject_CheckBuffer(args)) {
                PyErr_SetString(PyExc_TypeError, "no buffer interface");
                return NULL;
            }
            if (PyObject_GetBuffer(args, &view, PyBUF_SIMPLE) != 0) {
                return NULL;
            }
            PyObject *ret = view.obj;
            Py_INCREF(ret);
            PyBuffer_Release(&view);
            return ret;
            """)])
        class B():
            def __buffer__(self, flags):
                return memoryview(b'hello')
        
        ret = module.getbuffer(B())
        assert ret == b'hello'     

    def test_argparse(self):
        # issue 5136
        module = self.import_extension("foo", [
        ("getbuffer", "METH_VARARGS", """
            Py_buffer buf;
            if (!PyArg_ParseTuple(args, "y*", &buf))
                return NULL;
            int ro = buf.readonly;
            PyBuffer_Release(&buf);
            return PyLong_FromLong(ro);
        """),
        ])
        # buf = array.array("B", [0] * 1024)
        buf = bytearray(1024)
        # buf = (ctypes.c_uint8 * 1024)()
        ret = module.getbuffer(buf)
        for i in range(2000):
            assert ret == 0, "failed in iteration %d" % i

    def test_bytearray_release_buffer_unlocks_resize(self):
        # Acquire and immediately release: bytearray must be resizable after.
        # Also verify that holding the buffer blocks resize until release.
        module = self.import_extension("foo", [
            ("acquire_and_release", "METH_O",
             """
             Py_buffer buf;
             if (PyObject_GetBuffer(args, &buf, PyBUF_SIMPLE) < 0)
                 return NULL;
             PyBuffer_Release(&buf);
             Py_RETURN_NONE;
             """),
            ("acquire", "METH_O",
             """
             Py_buffer *buf = (Py_buffer *)malloc(sizeof(Py_buffer));
             if (PyObject_GetBuffer(args, buf, PyBUF_SIMPLE) < 0) {
                 free(buf);
                 return NULL;
             }
             return PyLong_FromVoidPtr(buf);
             """),
            ("release", "METH_O",
             """
             Py_buffer *buf = (Py_buffer *)PyLong_AsVoidPtr(args);
             PyBuffer_Release(buf);
             free(buf);
             Py_RETURN_NONE;
             """),
        ])
        b = bytearray(b'hello')
        module.acquire_and_release(b)
        b.append(ord('x'))
        assert b == bytearray(b'hellox')

        b2 = bytearray(b'world')
        token = module.acquire(b2)
        raises(BufferError, b2.append, ord('!'))
        module.release(token)
        b2.append(ord('!'))
        assert b2 == bytearray(b'world!')
