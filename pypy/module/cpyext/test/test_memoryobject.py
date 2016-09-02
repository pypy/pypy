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


class AppTestBufferProtocol(AppTestCpythonExtensionBase):
    def test_buffer_protocol(self):
        import struct
        module = self.import_module(name='buffer_test')
        arr = module.PyMyArray(10)
        y = memoryview(arr)
        assert y.format == 'i'
        assert y.shape == (10,)
        assert len(y) == 10
        s = y[3]
        assert len(s) == struct.calcsize('i')
        assert s == struct.pack('i', 3)
        viewlen = module.test_buffer(arr)
        assert viewlen == y.itemsize * len(y)

    def test_buffer_info(self):
        from _numpypy import multiarray as np
        module = self.import_module(name='buffer_test')
        get_buffer_info = module.get_buffer_info
        # test_export_flags from numpy test_multiarray
        raises(ValueError, get_buffer_info, np.arange(5)[::2], ('SIMPLE',))
        # test_relaxed_strides from numpy test_multiarray
        arr = np.zeros((1, 10))
        if arr.flags.f_contiguous:
            shape, strides = get_buffer_info(arr, ['F_CONTIGUOUS'])
            assert strides[0] == 8
            arr = np.ones((10, 1), order='F')
            shape, strides = get_buffer_info(arr, ['C_CONTIGUOUS'])
            assert strides[-1] == 8

