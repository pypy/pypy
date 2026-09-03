from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestMapping(AppTestCpythonExtensionBase):
    def test_check(self):
        module = self.import_extension('foo', [
            ("check", "METH_O", """
                PyObject *obj = args == Py_None ? NULL : args;
                return PyLong_FromLong(PyMapping_Check(obj));
            """),
            ])
        assert module.check({1: 2})
        # list and tuple have mp_subscript in CPython, so they count too
        assert module.check([1, 2])
        assert module.check((1, 2))
        assert module.check('abc')
        assert module.check(b'abc')
        assert not module.check(42)
        assert not module.check(object())
        assert not module.check(None)

    def test_size(self):
        module = self.import_extension('foo', [
            ("size", "METH_O", """
                PyObject *obj = args == Py_None ? NULL : args;
                Py_ssize_t r = PyMapping_Size(obj);
                if (r == -1 && PyErr_Occurred())
                    return NULL;
                return PyLong_FromSsize_t(r);
            """),
            ("length", "METH_O", """
                PyObject *obj = args == Py_None ? NULL : args;
                Py_ssize_t r = PyMapping_Length(obj);
                if (r == -1 && PyErr_Occurred())
                    return NULL;
                return PyLong_FromSsize_t(r);
            """),
            ])
        d = {'a': 'b'}
        assert module.size(d) == 1
        assert module.length(d) == 1
        raises(SystemError, module.size, None)
        raises(SystemError, module.length, None)

    def test_keys(self):
        module = self.import_extension('foo', [
            ("keys", "METH_O", """
                PyObject *obj = args == Py_None ? NULL : args;
                return PyMapping_Keys(obj);
            """),
            ("values", "METH_O", """
                PyObject *obj = args == Py_None ? NULL : args;
                return PyMapping_Values(obj);
            """),
            ("items", "METH_O", """
                PyObject *obj = args == Py_None ? NULL : args;
                return PyMapping_Items(obj);
            """),
            ])
        d = {'a': 'b'}
        assert module.keys(d) == ['a']
        assert module.values(d) == ['b']
        assert module.items(d) == [('a', 'b')]
        raises(SystemError, module.keys, None)
        raises(SystemError, module.values, None)
        raises(SystemError, module.items, None)

    def test_setitemstring(self):
        module = self.import_extension('foo', [
            ("setitemstring", "METH_VARARGS", """
                PyObject *obj, *key, *value;
                char *s;
                if (!PyArg_ParseTuple(args, "OOO", &obj, &key, &value))
                    return NULL;
                obj = obj == Py_None ? NULL : obj;
                s = key == Py_None ? NULL : PyBytes_AsString(key);
                value = value == Py_None ? NULL : value;
                if (PyMapping_SetItemString(obj, s, value) < 0)
                    return NULL;
                Py_RETURN_NONE;
            """),
            ("getitemstring", "METH_VARARGS", """
                PyObject *obj, *key;
                char *s;
                if (!PyArg_ParseTuple(args, "OO", &obj, &key))
                    return NULL;
                obj = obj == Py_None ? NULL : obj;
                s = key == Py_None ? NULL : PyBytes_AsString(key);
                return PyMapping_GetItemString(obj, s);
            """),
            ])
        d = {}
        module.setitemstring(d, b'key', 42)
        assert d == {'key': 42}
        assert module.getitemstring(d, b'key') == 42
        raises(KeyError, module.getitemstring, d, b'missing')
        raises(TypeError, module.getitemstring, 42, b'key')
        raises(TypeError, module.getitemstring, [], b'key')
        raises(UnicodeDecodeError, module.getitemstring, {}, b'\xff')
        raises(SystemError, module.getitemstring, {}, None)
        raises(SystemError, module.getitemstring, None, b'key')

        raises(TypeError, module.setitemstring, 42, b'key', 1)
        raises(UnicodeDecodeError, module.setitemstring, {}, b'\xff', 1)
        raises(SystemError, module.setitemstring, {}, None, 1)
        raises(SystemError, module.setitemstring, {}, b'key', None)
        raises(TypeError, module.setitemstring, [], b'key', 1)
        raises(SystemError, module.setitemstring, None, b'key', 1)

    def test_haskey(self):
        module = self.import_extension('foo', [
            ("haskey", "METH_VARARGS", """
                PyObject *obj, *key;
                if (!PyArg_ParseTuple(args, "OO", &obj, &key))
                    return NULL;
                obj = obj == Py_None ? NULL : obj;
                key = key == Py_None ? NULL : key;
                return PyLong_FromLong(PyMapping_HasKey(obj, key));
            """),
            ])
        d = {'a': 'b'}
        assert module.haskey(d, 'a')
        assert not module.haskey(d, 'b')
        assert module.haskey(d, d) == 0
        # and no error is set
        assert not module.haskey({}, None)
        assert not module.haskey(None, 'a')
