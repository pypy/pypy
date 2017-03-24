from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
import pytest

class AppTestBufferProtocol(AppTestCpythonExtensionBase):
    """Tests for the old buffer protocol."""

    def w_get_buffer_support(self):
        return self.import_extension('buffer_support', [
            ("charbuffer_as_string", "METH_O",
             """
                 char *ptr;
                 Py_ssize_t size;
                 if (PyObject_AsCharBuffer(args, (const char **)&ptr, &size) < 0)
                     return NULL;
                 return PyString_FromStringAndSize(ptr, size);
             """),
            ("check_readbuffer", "METH_O",
             """
                 return PyBool_FromLong(PyObject_CheckReadBuffer(args));
             """),
            ("readbuffer_as_string", "METH_O",
             """
                 const void *ptr;
                 Py_ssize_t size;
                 if (PyObject_AsReadBuffer(args, &ptr, &size) < 0)
                     return NULL;
                 return PyString_FromStringAndSize((char*)ptr, size);
             """),
            ("writebuffer_as_string", "METH_O",
             """
                 void *ptr;
                 Py_ssize_t size;
                 if (PyObject_AsWriteBuffer(args, &ptr, &size) < 0)
                     return NULL;
                 return PyString_FromStringAndSize((char*)ptr, size);
             """),
            ("zero_out_writebuffer", "METH_O",
             """
                 void *ptr;
                 Py_ssize_t size;
                 Py_ssize_t i;
                 if (PyObject_AsWriteBuffer(args, &ptr, &size) < 0)
                     return NULL;
                 for (i = 0; i < size; i++) {
                     ((char*)ptr)[i] = 0;
                 }
                 Py_RETURN_NONE;
             """),
            ])

    def test_string(self):
        buffer_support = self.get_buffer_support()

        s = 'a\0x'

        assert buffer_support.check_readbuffer(s)
        assert s == buffer_support.readbuffer_as_string(s)
        assert raises(TypeError, buffer_support.writebuffer_as_string, s)
        assert s == buffer_support.charbuffer_as_string(s)

    def test_buffer(self):
        buffer_support = self.get_buffer_support()

        s = 'a\0x'
        buf = buffer(s)

        assert buffer_support.check_readbuffer(buf)
        assert s == buffer_support.readbuffer_as_string(buf)
        assert raises(TypeError, buffer_support.writebuffer_as_string, buf)
        assert s == buffer_support.charbuffer_as_string(buf)

    def test_mmap(self):
        import mmap
        buffer_support = self.get_buffer_support()

        s = 'a\0x'
        mm = mmap.mmap(-1, 3)
        mm[:] = s

        assert buffer_support.check_readbuffer(mm)
        assert s == buffer_support.readbuffer_as_string(mm)
        assert s == buffer_support.writebuffer_as_string(mm)
        assert s == buffer_support.charbuffer_as_string(mm)

        s = '\0' * 3
        buffer_support.zero_out_writebuffer(mm)
        assert s == ''.join(mm)
        assert s == buffer_support.readbuffer_as_string(mm)
        assert s == buffer_support.writebuffer_as_string(mm)
        assert s == buffer_support.charbuffer_as_string(mm)

        s = '\0' * 3
        ro_mm = mmap.mmap(-1, 3, access=mmap.ACCESS_READ)
        assert buffer_support.check_readbuffer(ro_mm)
        assert s == buffer_support.readbuffer_as_string(ro_mm)
        assert raises(TypeError, buffer_support.writebuffer_as_string, ro_mm)
        assert s == buffer_support.charbuffer_as_string(ro_mm)

    def test_nonbuffer(self):
        # e.g. int
        buffer_support = self.get_buffer_support()

        assert not buffer_support.check_readbuffer(42)
        assert raises(TypeError, buffer_support.readbuffer_as_string, 42)
        assert raises(TypeError, buffer_support.writebuffer_as_string, 42)
        assert raises(TypeError, buffer_support.charbuffer_as_string, 42)

    def test_user_class(self):
        class MyBuf(str):
            pass
        s = 'a\0x'
        buf = MyBuf(s)
        buffer_support = self.get_buffer_support()

        assert buffer_support.check_readbuffer(buf)
        assert s == buffer_support.readbuffer_as_string(buf)
        assert raises(TypeError, buffer_support.writebuffer_as_string, buf)
        assert s == buffer_support.charbuffer_as_string(buf)


