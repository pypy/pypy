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
        if not self.runappdirect:
            skip('too slow, run with -A')
        module = self.import_extension('foo', [
            ("test_mod", 'METH_VARARGS',
            """
                PyObject *obj, *collect, *tup;
                Py_buffer bp;
                char expected_i = '0';
                if (!PyArg_ParseTuple(args, "OO", &obj, &collect))
                    return NULL;

                assert(obj);

                if (PyObject_GetBuffer(obj, &bp, PyBUF_SIMPLE) == -1)
                    return NULL;
                
                tup = PyTuple_New(0); /* for collect() */
                for (size_t i = 0; i < bp.len; ++i)
                {
                    if (((unsigned char*)bp.buf)[i] == expected_i)
                    {
                        if (++expected_i >= '8')
                            expected_i = '0';
                    }
                    else
                    {
                        PyErr_Format(PyExc_ValueError,
                                "mismatch: 0x%x [%x %x %x %x...] instead of 0x%x on pos=%d (got len=%d)",
                                ((unsigned char*)bp.buf)[i],
                                ((unsigned char*)bp.buf)[i+1],
                                ((unsigned char*)bp.buf)[i+2],
                                ((unsigned char*)bp.buf)[i+3],
                        ((unsigned char*)bp.buf)[i+4],
                        expected_i, i, bp.len);
                        PyBuffer_Release(&bp);
                        Py_DECREF(tup);
                        return NULL;
                    }
                }

                PyBuffer_Release(&bp);
                Py_DECREF(tup);
                Py_RETURN_NONE;
            """),
            ])
        import io, gc
        bufsize = 4096
        def getdata(bufsize):
            data = b'01234567'
            for x in range(18):
                data += data
                if len(data) >= bufsize:
                    break
            return data
        for j, block in enumerate(iter(lambda: getdata(bufsize), b'')):
            try:
                module.test_mod(block, gc.collect)
            except ValueError as e:
                print("%s at it=%d" % (e, j))
                assert False
            if j > 2000:
                break
