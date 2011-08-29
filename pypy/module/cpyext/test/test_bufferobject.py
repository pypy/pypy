from pypy.rpython.lltypesystem import rffi, lltype
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
                 if (PyObject_AsCharBuffer(args, &ptr, &size) < 0)
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
