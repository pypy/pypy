from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.object import Py_PRINT_RAW
from rpython.rtyper.lltypesystem import rffi
from rpython.tool.udir import udir
import pytest

class TestFile(BaseApiTest):

    def test_file_fromstring(self, space, api):
        filename = rffi.str2charp(str(udir / "_test_file"))
        mode = rffi.str2charp("wb")
        w_file = api.PyFile_FromString(filename, mode)
        rffi.free_charp(filename)
        rffi.free_charp(mode)

        space.call_method(w_file, "write", space.newbytes("text"))
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
    def test_file_setbufsize(self, space, api):
        api.PyFile_SetBufSize()

    def test_file_writestring(self, space, api, capfd):
        w_stdout = space.sys.get("stdout")
        with rffi.scoped_str2charp("test\n") as s:
            api.PyFile_WriteString(s, w_stdout)
        space.call_method(w_stdout, "flush")
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
