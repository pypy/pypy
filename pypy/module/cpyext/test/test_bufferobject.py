from rpython.rtyper.lltypesystem import lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.api import PyObject

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


    def test_issue2752(self):
        iterations = 10
        if self.runappdirect:
            iterations = 2000
        module = self.import_extension('foo', [
            ("test_mod", 'METH_VARARGS',
            """
                PyObject *obj;
                Py_buffer bp;
                if (!PyArg_ParseTuple(args, "O", &obj))
                    return NULL;

                if (PyObject_GetBuffer(obj, &bp, PyBUF_SIMPLE) == -1)
                    return NULL;
                
                if (((unsigned char*)bp.buf)[0] != '0') {
                    void * buf = (void*)bp.buf;
                    unsigned char val[4];
                    char * s = PyString_AsString(obj);
                    memcpy(val, bp.buf, 4);
                    PyBuffer_Release(&bp);
                    if (PyObject_GetBuffer(obj, &bp, PyBUF_SIMPLE) == -1)
                        return NULL;
                    PyErr_Format(PyExc_ValueError,
                            "mismatch: %p [%x %x %x %x...] now %p [%x %x %x %x...] as str '%s'",
                            buf, val[0], val[1], val[2], val[3],
                            (void *)bp.buf,
                            ((unsigned char*)bp.buf)[0],
                            ((unsigned char*)bp.buf)[1],
                            ((unsigned char*)bp.buf)[2],
                            ((unsigned char*)bp.buf)[3],
                            s);
                    PyBuffer_Release(&bp);
                    return NULL;
                }

                PyBuffer_Release(&bp);
                Py_RETURN_NONE;
            """),
            ])
        bufsize = 4096
        def getdata(bufsize):
            data = b'01234567'
            for x in range(18):
                data += data
                if len(data) >= bufsize:
                    break
            return data
        for j in range(iterations):
            block = getdata(bufsize)
            assert block[:8] == '01234567'
            try:
                module.test_mod(block)
            except ValueError as e:
                print("%s at it=%d" % (e, j))
                assert False
