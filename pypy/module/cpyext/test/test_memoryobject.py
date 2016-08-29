from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class TestMemoryViewObject(BaseApiTest):
    def test_fromobject(self, space, api):
        w_hello = space.newbytes("hello")
        assert api.PyObject_CheckBuffer(w_hello)
        w_view = api.PyMemoryView_FromObject(w_hello)
        w_char = space.call_method(w_view, '__getitem__', space.wrap(0))
        assert space.eq_w(w_char, space.wrap('h'))
        w_bytes = space.call_method(w_view, "tobytes")
        assert space.unwrap(w_bytes) == "hello"

class AppTestPyBuffer_FillInfo(AppTestCpythonExtensionBase):
    def test_fillWithObject(self):
        module = self.import_extension('foo', [
                ("fillinfo", "METH_VARARGS",
                 """
                 Py_buffer buf;
                 PyObject *str = PyBytes_FromString("hello, world.");
                 if (PyBuffer_FillInfo(&buf, str, PyBytes_AsString(str), 13,
                                       0, 0)) {
                     return NULL;
                 }

                 /* Get rid of our own reference to the object, but
                  * the Py_buffer should still have a reference.
                  */
                 Py_DECREF(str);

                 return PyMemoryView_FromBuffer(&buf);
                 """)])
        result = module.fillinfo()
        assert b"hello, world." == result
        del result

    def test_fill_from_NULL_pointer(self):
        module = self.import_extension('foo', [
                ("fillinfo_NULL", "METH_VARARGS",
                 """
                 Py_buffer info;
                 if (PyBuffer_FillInfo(&info, NULL, NULL, 1, 1,
                                       PyBUF_FULL_RO) < 0) {
                     return NULL;
                 }
                 return PyMemoryView_FromBuffer(&info);
                 """)])
        exc = raises(ValueError, module.fillinfo_NULL)
        expected = ("cannot make memory view from a buffer with a NULL data "
                    "pointer")
        assert str(exc.value) == expected

    @pytest.mark.skipif(True, reason='write a test for this')
    def test_get_base_and_get_buffer(self, space, api):
        assert False # XXX test PyMemoryView_GET_BASE, PyMemoryView_GET_BUFFER

class AppTestBufferProtocol(AppTestCpythonExtensionBase):
    def test_buffer_protocol(self):
        import struct
        module = self.import_module(name='buffer_test')
        arr = module.PyMyArray(10)
        y = memoryview(arr)
        assert y.format == 'i'
        assert y.shape == (10,)
        s = y[3]
        assert len(s) == struct.calcsize('i')
        assert s == struct.pack('i', 3)
