import pytest
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class TestMemoryViewObject(BaseApiTest):
    def test_fromobject(self, space, api):
        if space.is_true(space.lt(space.sys.get('version_info'),
                                  space.wrap((2, 7)))):
            py.test.skip("unsupported before Python 2.7")

        w_hello = space.newbytes("hello")
        w_view = api.PyMemoryView_FromObject(w_hello)
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
