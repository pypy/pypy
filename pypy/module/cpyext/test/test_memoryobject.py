import pytest

from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rlib.buffer import StringBuffer

only_pypy ="config.option.runappdirect and '__pypy__' not in sys.builtin_module_names" 

class TestMemoryViewObject(BaseApiTest):
    skip('needs c_bf_getbuffer wrapper from slotdefs')
    def test_fromobject(self, space, api):
        w_hello = space.newbytes("hello")
        assert api.PyObject_CheckBuffer(w_hello)
        w_view = api.PyMemoryView_FromObject(w_hello)
        w_char = space.call_method(w_view, '__getitem__', space.wrap(0))
        assert space.eq_w(w_char, space.wrap('h'))
        w_bytes = space.call_method(w_view, "tobytes")
        assert space.unwrap(w_bytes) == "hello"

    def test_frombuffer(self, space, api):
        w_buf = space.newbuffer(StringBuffer("hello"))
        w_memoryview = api.PyMemoryView_FromObject(w_buf)
        w_view = api.PyMemoryView_GET_BUFFER(w_memoryview)
        assert w_view.c_ndim == 1
        f = rffi.charp2str(w_view.c_format)
        assert f == 'B'
        assert w_view.c_shape[0] == 5
        assert w_view.c_strides[0] == 1
        assert w_view.c_len == 5
        o = rffi.charp2str(w_view.c_buf)
        assert o == 'hello'

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

    @pytest.mark.skipif(only_pypy, reason='pypy only test')
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
