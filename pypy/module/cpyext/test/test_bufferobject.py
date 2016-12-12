from rpython.rtyper.lltypesystem import lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.api import PyObject
from pypy.module.cpyext.pyobject import Py_DecRef

class AppTestBufferObject(AppTestCpythonExtensionBase):
    def test_FromMemory(self):
        module = self.import_extension('foo', [
            ("get_FromMemory", "METH_NOARGS",
             """
                 cbuf = malloc(4);
                 cbuf[0] = 'a';
                 cbuf[1] = 'b';
                 cbuf[2] = 'c';
                 cbuf[3] = '\\0';
                 return PyBuffer_FromMemory(cbuf, 4);
             """),
            ("free_buffer", "METH_NOARGS",
             """
                 free(cbuf);
                 Py_RETURN_NONE;
             """),
            ("check_ascharbuffer", "METH_O",
             """
                 char *ptr;
                 Py_ssize_t size;
                 if (PyObject_AsCharBuffer(args, (const char **)&ptr, &size) < 0)
                     return NULL;
                 return PyString_FromStringAndSize(ptr, size);
             """)
            ], prologue = """
            static char* cbuf = NULL;
            """)
        buf = module.get_FromMemory()
        assert str(buf) == 'abc\0'

        assert module.check_ascharbuffer(buf) == 'abc\0'

        module.free_buffer()

    def test_Buffer_New(self):
        module = self.import_extension('foo', [
            ("buffer_new", "METH_NOARGS",
             """
                 return PyBuffer_New(150);
             """),
            ])
        b = module.buffer_new()
        raises(AttributeError, getattr, b, 'x')

    def test_array_buffer(self):
        if self.runappdirect:
            skip('PyBufferObject not available outside buffer object.c')
        module = self.import_extension('foo', [
            ("roundtrip", "METH_O",
             """
                 PyBufferObject *buf = (PyBufferObject *)args;
                 return PyString_FromStringAndSize(buf->b_ptr, buf->b_size);
             """),
            ])
        import array
        a = array.array('c', 'text')
        b = buffer(a)
        assert module.roundtrip(b) == 'text'
        
    def test_releasebuffer(self):
        module = self.import_extension('foo', [
            ("create_test", "METH_NOARGS",
             """
                PyObject *obj;
                obj = PyObject_New(PyObject, (PyTypeObject*)type);
                return obj;
             """),
            ("get_cnt", "METH_NOARGS",
             'return PyLong_FromLong(cnt);')], prologue="""
                static float test_data = 42.f;
                static int cnt=0;
                static PyHeapTypeObject * type=NULL;

                int getbuffer(PyObject *obj, Py_buffer *view, int flags) {

                    cnt ++;
                    memset(view, 0, sizeof(Py_buffer));
                    view->obj = obj;
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

                type->ht_type.tp_as_buffer = &type->as_buffer;
                type->as_buffer.bf_getbuffer = getbuffer;
                type->as_buffer.bf_releasebuffer = releasebuffer;

                if (PyType_Ready(&type->ht_type) < 0) INITERROR;
            """, )
        import gc
        assert module.get_cnt() == 0
        a = memoryview(module.create_test())
        assert module.get_cnt() == 1
        del a
        assert module.get_cnt() == 0
