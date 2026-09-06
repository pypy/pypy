from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestFileObject(AppTestCpythonExtensionBase):
    def test_defaultencoding(self):
        import sys
        module = self.import_extension('foo', [
            ("defenc", "METH_NOARGS",
             """
                return PyUnicode_FromString(Py_FileSystemDefaultEncoding);
             """),
            ("getline", "METH_VARARGS",
             """
                PyObject *obj;
                int n;
                if (!PyArg_ParseTuple(args, "Oi", &obj, &n))
                    return NULL;
                return PyFile_GetLine(obj, n);
             """),
            ])
        assert module.defenc() == sys.getfilesystemencoding()

        import io
        f = io.StringIO("line1\nline2\nline3\nline4")
        assert module.getline(f, 0) == "line1\n"
        assert module.getline(f, 4) == "line"
        assert module.getline(f, 0) == "2\n"
        # for n < 0, a trailing newline (if any) is stripped, unlike n >= 0
        assert module.getline(f, -1) == "line3"
        # last line has no trailing newline, so nothing to strip
        assert module.getline(f, -1) == "line4"
        raises(EOFError, module.getline, f, -1)
