from pypy.module.cpyext.api import fopen, fclose, fwrite
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.object import Py_PRINT_RAW
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.tool.udir import udir
import pytest

class TestFile(BaseApiTest):

    def test_file_fromstring(self, space, api):
        filename = rffi.str2charp(str(udir / "_test_file"))
        mode = rffi.str2charp("wb")
        w_file = api.PyFile_FromString(filename, mode)
        rffi.free_charp(filename)
        rffi.free_charp(mode)

        assert api.PyFile_Check(w_file)
        assert api.PyFile_CheckExact(w_file)
        assert not api.PyFile_Check(space.wrap("text"))

        space.call_method(w_file, "write", space.wrap("text"))
        space.call_method(w_file, "close")
        assert (udir / "_test_file").read() == "text"

    def test_file_getline(self, space, api):
        filename = rffi.str2charp(str(udir / "_test_file"))

        mode = rffi.str2charp("w")
        w_file = api.PyFile_FromString(filename, mode)
        space.call_method(w_file, "write",
                          space.wrap("line1\nline2\nline3\nline4"))
        space.call_method(w_file, "close")

        rffi.free_charp(mode)
        mode = rffi.str2charp("r")
        w_file = api.PyFile_FromString(filename, mode)
        rffi.free_charp(filename)
        rffi.free_charp(mode)

        w_line = api.PyFile_GetLine(w_file, 0)
        assert space.str_w(w_line) == "line1\n"

        w_line = api.PyFile_GetLine(w_file, 4)
        assert space.str_w(w_line) == "line"

        w_line = api.PyFile_GetLine(w_file, 0)
        assert space.str_w(w_line) == "2\n"

        # XXX We ought to raise an EOFError here, but don't
        w_line = api.PyFile_GetLine(w_file, -1)
        # assert api.PyErr_Occurred() is space.w_EOFError
        assert space.str_w(w_line) == "line3\n"

        space.call_method(w_file, "close")

    def test_file_name(self, space, api):
        name = str(udir / "_test_file")
        with rffi.scoped_str2charp(name) as filename:
            with rffi.scoped_str2charp("wb") as mode:
                w_file = api.PyFile_FromString(filename, mode)
        assert space.str_w(api.PyFile_Name(w_file)) == name

    @pytest.mark.xfail
    def test_file_fromfile(self, space, api):
        api.PyFile_Fromfile()

    @pytest.mark.xfail
    def test_file_setbufsize(self, space, api):
        api.PyFile_SetBufSize()

    def test_file_writestring(self, space, api, capfd):
        s = rffi.str2charp("test\n")
        try:
            api.PyFile_WriteString(s, space.sys.get("stdout"))
        finally:
            rffi.free_charp(s)
        out, err = capfd.readouterr()
        out = out.replace('\r\n', '\n')
        assert out == "test\n"

    def test_file_writeobject(self, space, api, capfd):
        w_obj = space.wrap("test\n")
        w_stdout = space.sys.get("stdout")
        api.PyFile_WriteObject(w_obj, w_stdout, Py_PRINT_RAW)
        api.PyFile_WriteObject(w_obj, w_stdout, 0)
        space.call_method(w_stdout, "flush")
        out, err = capfd.readouterr()
        out = out.replace('\r\n', '\n')
        assert out == "test\n'test\\n'"

    def test_file_softspace(self, space, api, capfd):
        w_stdout = space.sys.get("stdout")
        assert api.PyFile_SoftSpace(w_stdout, 1) == 0
        assert api.PyFile_SoftSpace(w_stdout, 0) == 1
        
        api.PyFile_SoftSpace(w_stdout, 1)
        w_ns = space.newdict()
        space.exec_("print 1,", w_ns, w_ns)
        space.exec_("print 2,", w_ns, w_ns)
        api.PyFile_SoftSpace(w_stdout, 0)
        space.exec_("print 3", w_ns, w_ns)
        space.call_method(w_stdout, "flush")
        out, err = capfd.readouterr()
        out = out.replace('\r\n', '\n')
        assert out == " 1 23\n"
