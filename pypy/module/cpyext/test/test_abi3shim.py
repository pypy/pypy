from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestAbi3Shim(AppTestCpythonExtensionBase):
    """The abi3 (limited-API) surface that CPython exports but PyPy does not
    yet implement is filled by useless shims: each missing function is either
    an 'error' shim (sets NotImplementedError and returns an error sentinel) or
    an 'ignore' shim (a no-op).  This test only checks that the symbols are
    declared in the headers, link, and behave as shims - not that they do the
    real work."""

    def test_error_shims_pointer(self):
        module = self.import_extension('foo', [
            ("type_frommetaclass", "METH_NOARGS", """
                return PyType_FromMetaclass(NULL, NULL, NULL, NULL);
            """),
            ("decodeerror_getencoding", "METH_NOARGS", """
                return PyUnicodeDecodeError_GetEncoding(Py_None);
            """),
            ("unicode_partition", "METH_NOARGS", """
                return PyUnicode_Partition(Py_None, Py_None);
            """),
            ("float_getinfo", "METH_NOARGS", """
                return PyFloat_GetInfo();
            """),
            ])
        raises(NotImplementedError, module.type_frommetaclass)
        raises(NotImplementedError, module.decodeerror_getencoding)
        raises(NotImplementedError, module.unicode_partition)
        raises(NotImplementedError, module.float_getinfo)

    def test_error_shims_int(self):
        module = self.import_extension('foo', [
            ("codec_register", "METH_NOARGS", """
                if (PyCodec_Register(Py_None) < 0)
                    return NULL;
                Py_RETURN_NONE;
            """),
            ("import_getmagicnumber", "METH_NOARGS", """
                long m = PyImport_GetMagicNumber();
                if (m == -1 && PyErr_Occurred())
                    return NULL;
                return PyLong_FromLong(m);
            """),
            ])
        raises(NotImplementedError, module.codec_register)
        raises(NotImplementedError, module.import_getmagicnumber)

    def test_ignore_shims_void(self):
        module = self.import_extension('foo', [
            ("initialize", "METH_NOARGS", """
                Py_Initialize();
                Py_RETURN_NONE;
            """),
            ("afterfork_child", "METH_NOARGS", """
                PyOS_AfterFork_Child();
                Py_RETURN_NONE;
            """),
            ])
        assert module.initialize() is None
        assert module.afterfork_child() is None

    def test_predicate_shim_returns_false(self):
        module = self.import_extension('foo', [
            ("aiter_check", "METH_O", """
                return PyLong_FromLong(PyAIter_Check(args));
            """),
            ])
        assert module.aiter_check(object()) == 0

    def test_macro_maps_to_macro(self):
        module = self.import_extension('foo', [
            ("long_frompid", "METH_NOARGS", """
                return PyLong_FromPid(4321);
            """),
            ("dictitems_check", "METH_O", """
                return PyLong_FromLong(PyDictItems_Check(args));
            """),
            ("cfunction_checkexact", "METH_O", """
                return PyLong_FromLong(PyCFunction_CheckExact(args));
            """),
            ("seqiter_check", "METH_O", """
                return PyLong_FromLong(PySeqIter_Check(args));
            """),
            ("calliter_check", "METH_O", """
                return PyLong_FromLong(PyCallIter_Check(args));
            """),
            ("is_true", "METH_O", """
                return PyLong_FromLong(Py_IsTrue(args));
            """),
            ("is_false", "METH_O", """
                return PyLong_FromLong(Py_IsFalse(args));
            """),
            ])
        assert module.long_frompid() == 4321

        assert module.dictitems_check({}.items()) == 1
        assert module.dictitems_check([]) == 0

        # a function defined by this C extension is a real PyCFunction
        assert module.cfunction_checkexact(module.long_frompid) == 1
        assert module.cfunction_checkexact(object()) == 0

        class S(object):
            def __getitem__(self, i):
                raise IndexError
        assert module.seqiter_check(iter(S())) == 1
        assert module.seqiter_check([]) == 0

        assert module.calliter_check(iter(lambda: 0, 1)) == 1
        assert module.calliter_check([]) == 0

        assert module.is_true(True) == 1
        assert module.is_true(False) == 0
        assert module.is_true(1) == 0
        assert module.is_false(False) == 1
        assert module.is_false(True) == 0
        assert module.is_false(0) == 0
