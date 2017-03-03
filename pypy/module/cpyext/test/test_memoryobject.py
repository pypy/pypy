import pytest

from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rlib.buffer import StringBuffer
from pypy.module.cpyext.pyobject import from_ref
from pypy.module.cpyext.memoryobject import PyMemoryViewObject

only_pypy ="config.option.runappdirect and '__pypy__' not in sys.builtin_module_names"

class TestMemoryViewObject(BaseApiTest):
    def test_frombuffer(self, space, api):
        w_buf = space.newbuffer(StringBuffer("hello"))
        c_memoryview = rffi.cast(
            PyMemoryViewObject, api.PyMemoryView_FromObject(w_buf))
        w_memoryview = from_ref(space, c_memoryview)
        view = c_memoryview.c_view
        assert view.c_ndim == 1
        f = rffi.charp2str(view.c_format)
        assert f == 'B'
        assert view.c_shape[0] == 5
        assert view.c_strides[0] == 1
        assert view.c_len == 5
        o = rffi.charp2str(view.c_buf)
        assert o == 'hello'
        ref = api.PyMemoryView_FromBuffer(view)
        w_mv = from_ref(space, ref)
        for f in ('format', 'itemsize', 'ndim', 'readonly',
                  'shape', 'strides', 'suboffsets'):
            w_f = space.wrap(f)
            assert space.eq_w(space.getattr(w_mv, w_f),
                              space.getattr(w_memoryview, w_f))
        api.Py_DecRef(ref)

class AppTestPyBuffer_FillInfo(AppTestCpythonExtensionBase):
    def test_fillWithObject(self):
        module = self.import_extension('foo', [
                ("fillinfo", "METH_VARARGS",
                 """
                 Py_buffer buf;
                 PyObject * ret = NULL;
                 PyObject *str = PyBytes_FromString("hello, world.");
                 if (PyBuffer_FillInfo(&buf, str, PyBytes_AsString(str), 13,
                                       0, 0)) {
                     return NULL;
                 }

                 /* Get rid of our own reference to the object, but
                  * the Py_buffer should still have a reference.
                  */
                 Py_DECREF(str);

                 ret = PyMemoryView_FromBuffer(&buf);
                 if (((PyMemoryViewObject*)ret)->view.obj != buf.obj)
                 {
                    PyErr_SetString(PyExc_ValueError, "leaked ref");
                    Py_DECREF(ret);
                    return NULL;
                 }
                 return ret;
                 """)])
        result = module.fillinfo()
        assert b"hello, world." == result
        del result

    def test_0d(self):
        module = self.import_extension('foo', [
            ("create_view", "METH_VARARGS",
             """
             /* Create an approximation of the buffer for a 0d ndarray */
             Py_buffer buf;
             PyObject *str = PyBytes_FromString("hello, world.");
             buf.buf = PyBytes_AsString(str);
             buf.obj = str;
             buf.readonly = 1;
             buf.len = 13;
             buf.itemsize = 13;
             buf.ndim = 0;
             buf.shape = NULL;
             PyObject* ret = PyMemoryView_FromBuffer(&buf);
             return ret;
            """)])
        result = module.create_view()
        assert result.shape == ()
        assert result.itemsize == 13
        assert result.tobytes() == b'hello, world.'

class AppTestBufferProtocol(AppTestCpythonExtensionBase):
    def test_fromobject(self):
        foo = self.import_extension('foo', [
            ("make_view", "METH_O",
             """
             if (!PyObject_CheckBuffer(args))
                return Py_None;
             return PyMemoryView_FromObject(args);
             """)])
        hello = b'hello'
        mview = foo.make_view(hello)
        assert mview[0] == hello[0]
        assert mview.tobytes() == hello

    def test_buffer_protocol_app(self):
        module = self.import_module(name='buffer_test')
        arr = module.PyMyArray(10)
        y = memoryview(arr)
        assert y.format == 'i'
        assert y.shape == (10,)
        assert len(y) == 10
        s = y[3]
        assert s == 3

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

    def test_releasebuffer(self):
        if not self.runappdirect:
            skip("Fails due to ll2ctypes nonsense")
        module = self.import_extension('foo', [
            ("create_test", "METH_NOARGS",
             """
                PyObject *obj;
                obj = PyObject_New(PyObject, (PyTypeObject*)type);
                return obj;
             """),
            ("get_cnt", "METH_NOARGS",
             'return PyLong_FromLong(cnt);'),
            ("get_dealloc_cnt", "METH_NOARGS",
             'return PyLong_FromLong(dealloc_cnt);'),
        ],
        prologue="""
                static float test_data = 42.f;
                static int cnt=0;
                static int dealloc_cnt=0;
                static PyHeapTypeObject * type=NULL;

                void dealloc(PyObject *self) {
                    dealloc_cnt++;
                }
                int getbuffer(PyObject *obj, Py_buffer *view, int flags) {

                    cnt ++;
                    memset(view, 0, sizeof(Py_buffer));
                    view->obj = obj;
                    /* see the CPython docs for why we need this incref:
                       https://docs.python.org/3.5/c-api/typeobj.html#c.PyBufferProcs.bf_getbuffer */
                    Py_INCREF(obj);
                    view->ndim = 0;
                    view->buf = (void *) &test_data;
                    view->itemsize = sizeof(float);
                    view->len = 1;
                    view->strides = NULL;
                    view->shape = NULL;
                    view->format = "f";
                    return 0;
                }

                void releasebuffer(PyObject *obj, Py_buffer *view) {
                    cnt --;
                }
            """, more_init="""
                type = (PyHeapTypeObject *) PyType_Type.tp_alloc(&PyType_Type, 0);

                type->ht_type.tp_name = "Test";
                type->ht_type.tp_basicsize = sizeof(PyObject);
                type->ht_name = PyString_FromString("Test");
                type->ht_type.tp_flags |= Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE |
                                          Py_TPFLAGS_HEAPTYPE | Py_TPFLAGS_HAVE_NEWBUFFER;
                type->ht_type.tp_flags &= ~Py_TPFLAGS_HAVE_GC;

                type->ht_type.tp_dealloc = dealloc;
                type->ht_type.tp_as_buffer = &type->as_buffer;
                type->as_buffer.bf_getbuffer = getbuffer;
                type->as_buffer.bf_releasebuffer = releasebuffer;

                if (PyType_Ready(&type->ht_type) < 0) INITERROR;
            """, )
        import gc
        assert module.get_cnt() == 0
        a = memoryview(module.create_test())
        assert module.get_cnt() == 1
        assert module.get_dealloc_cnt() == 0
        del a
        self.debug_collect()
        assert module.get_cnt() == 0
        assert module.get_dealloc_cnt() == 1
