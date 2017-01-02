import pytest

from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rlib.buffer import StringBuffer

only_pypy ="config.option.runappdirect and '__pypy__' not in sys.builtin_module_names"

class TestMemoryViewObject(BaseApiTest):
    def test_fromobject(self, space, api):
        w_hello = space.newbytes("hello")
        # implemented as a C macro
        #assert api.PyObject_CheckBuffer(w_hello)
        w_view = api.PyMemoryView_FromObject(w_hello)
        w_char = space.call_method(w_view, '__getitem__', space.wrap(0))
        assert space.eq_w(w_char, space.wrap('h'))
        w_bytes = space.call_method(w_view, "tobytes")
        assert space.unwrap(w_bytes) == "hello"

    def test_frombuffer(self, space, api):
        w_buf = space.newbuffer(StringBuffer("hello"))
        w_memoryview = api.PyMemoryView_FromObject(w_buf)
        view = api.PyMemoryView_GET_BUFFER(w_memoryview)
        assert view.c_ndim == 1
        f = rffi.charp2str(view.c_format)
        assert f == 'B'
        assert view.c_shape[0] == 5
        assert view.c_strides[0] == 1
        assert view.c_len == 5
        o = rffi.charp2str(view.c_buf)
        assert o == 'hello'
        w_mv = api.PyMemoryView_FromBuffer(view)
        for f in ('format', 'itemsize', 'ndim', 'readonly',
                  'shape', 'strides', 'suboffsets'):
            w_f = space.wrap(f)
            assert space.eq_w(space.getattr(w_mv, w_f),
                              space.getattr(w_memoryview, w_f))

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

class AppTestBufferProtocol(AppTestCpythonExtensionBase):
    def test_buffer_protocol_app(self):
        import struct
        module = self.import_module(name='buffer_test')
        arr = module.PyMyArray(10)
        y = memoryview(arr)
        assert y.format == 'i'
        assert y.shape == (10,)
        assert len(y) == 10
        assert y[3] == 3

    def test_buffer_protocol_capi(self):
        foo = self.import_extension('foo', [
            ("get_len", "METH_VARARGS",
             """
                Py_buffer view;
                PyObject* obj = PyTuple_GetItem(args, 0);
                long ret, vlen;
                memset(&view, 0, sizeof(Py_buffer));
                ret = PyObject_GetBuffer(obj, &view, PyBUF_FULL_RO);
                if (ret != 0)
                    return NULL;
                vlen = view.len / view.itemsize;
                PyBuffer_Release(&view);
                return PyLong_FromLong(vlen);
             """),
            ("test_buffer", "METH_VARARGS",
             """
                Py_buffer* view = NULL;
                PyObject* obj = PyTuple_GetItem(args, 0);
                PyObject* memoryview = PyMemoryView_FromObject(obj);
                if (memoryview == NULL)
                    return PyLong_FromLong(-1);
                view = PyMemoryView_GET_BUFFER(memoryview);
                Py_DECREF(memoryview);
                return PyLong_FromLong(view->len / view->itemsize);
            """)])
        module = self.import_module(name='buffer_test')
        arr = module.PyMyArray(10)
        ten = foo.get_len(arr)
        assert ten == 10
        ten = foo.get_len(b'1234567890')
        assert ten == 10
        ten = foo.test_buffer(arr)
        assert ten == 10

    @pytest.mark.skipif(True, reason="no _numpypy on py3k")
    #@pytest.mark.skipif(only_pypy, reason='pypy only test')
    def test_buffer_info(self):
        try:
            from _numpypy import multiarray as np
        except ImportError:
            skip('pypy built without _numpypy')
        module = self.import_module(name='buffer_test')
        get_buffer_info = module.get_buffer_info
        raises(ValueError, get_buffer_info, np.arange(5)[::2], ('SIMPLE',))
        arr = np.zeros((1, 10), order='F')
        shape, strides = get_buffer_info(arr, ['F_CONTIGUOUS'])
        assert strides[0] == 8
        arr = np.zeros((10, 1), order='C')
        shape, strides = get_buffer_info(arr, ['C_CONTIGUOUS'])
        assert strides[-1] == 8
        dt1 = np.dtype(
             [('a', 'b'), ('b', 'i'),
              ('sub0', np.dtype('b,i')),
              ('sub1', np.dtype('b,i')),
              ('sub2', np.dtype('b,i')),
              ('sub3', np.dtype('b,i')),
              ('sub4', np.dtype('b,i')),
              ('sub5', np.dtype('b,i')),
              ('sub6', np.dtype('b,i')),
              ('sub7', np.dtype('b,i')),
              ('c', 'i')],
             )
        x = np.arange(dt1.itemsize, dtype='int8').view(dt1)
        # pytest can catch warnings from v2.8 and up, we ship 2.5
        import warnings
        warnings.filterwarnings("error")
        try:
            try:
                y = get_buffer_info(x, ['SIMPLE'])
            except UserWarning as e:
                pass
            else:
                assert False ,"PyPy-specific UserWarning not raised" \
                          " on too long format string"
        finally:
            warnings.resetwarnings()
