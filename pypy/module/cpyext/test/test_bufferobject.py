from rpython.rlib.buffer import StringBuffer, SubBuffer
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.bufferobject import leak_stringbuffer
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


def test_leaked_buffer():
    s = 'hello world'
    buf = leak_stringbuffer(StringBuffer(s))
    assert buf.getitem(4) == 'o'
    assert buf.getitem(4) == buf[4]
    assert buf.getlength() == 11
    assert buf.getlength() == len(buf)
    assert buf.getslice(1, 6, 1, 5) == 'ello '
    assert buf.getslice(1, 6, 1, 5) == buf[1:6]
    assert buf.getslice(1, 6, 2, 3) == 'el '
    assert buf.as_str() == 'hello world'
    assert s == rffi.charp2str(buf.get_raw_address())
    rffi.free_charp(buf.get_raw_address())


def test_leaked_subbuffer():
    s = 'hello world'
    buf = leak_stringbuffer(SubBuffer(StringBuffer(s), 1, 10))
    assert buf.getitem(4) == ' '
    assert buf.getitem(4) == buf[4]
    assert buf.getlength() == 10
    assert buf.getlength() == len(buf)
    assert buf.getslice(1, 6, 1, 5) == 'llo w'
    assert buf.getslice(1, 6, 1, 5) == buf[1:6]
    assert buf.getslice(1, 6, 2, 3) == 'low'
    assert buf.as_str() == 'ello world'
    assert s[1:] == rffi.charp2str(buf.get_raw_address())
    rffi.free_charp(buf.buffer.get_raw_address())

