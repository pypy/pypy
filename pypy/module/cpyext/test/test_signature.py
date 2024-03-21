from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestSignature(AppTestCpythonExtensionBase):
    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)
        cls.w_make_module = cls.space.appexec(
            [],
            '''():
            def make_module(self, name, arg_types, ret_type, wrapper, impl):
                arg_types_str = ", ".join(arg_types)
                flags = "METH_O" if len(arg_types) == 1 else "METH_FASTCALL"
                body = """
                {0}
                {1}
                int {2}_arg_types[] = {{ {3}, -1 }};
                PyPyTypedMethodMetadata {2}_sig = {{
                  .arg_types = {2}_arg_types,
                  .ret_type = {4},
                  .underlying_func = {2}_impl,
                #define STR(x) #x
                  .ml_name = STR({2}),
                }};
                static PyMethodDef signature_methods[] = {{
                    {{ {2}_sig.ml_name, {2}, {5} | METH_TYPED, STR({2}) }},
                    {{NULL, NULL, 0, NULL}},
                }};
                static struct PyModuleDef signature_definition = {{
                    PyModuleDef_HEAD_INIT, "signature",
                    "A C extension module with type information exposed.", -1,
                    signature_methods,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                }};
                """.format(impl, wrapper, name, arg_types_str, ret_type, flags)
                init = """
                return PyModule_Create(&signature_definition);
                """
                return self.import_module(name="signature", body=body, init=init, use_imp=True)
            return make_module
        ''',
        )
        cls.w_func_inc = cls.space.newtuple(
            [
                cls.space.newtext("inc"),
                cls.space.newtuple([cls.space.newtext("T_C_LONG")]),
                cls.space.newtext("T_C_LONG"),
                cls.space.newtext(
                    """
PyObject* inc(PyObject* module, PyObject* obj) {
  (void)module;
  long obj_int = PyLong_AsLong(obj);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = inc_impl(obj_int);
  return PyLong_FromLong(result);
}"""
                ),
                cls.space.newtext(
                    """
long inc_impl(long arg) {
  return arg+1;
}"""
                ),
            ]
        )
        cls.w_func_raise_long = cls.space.newtuple(
            [
                cls.space.newtext("raise_long"),
                cls.space.newtuple([cls.space.newtext("T_C_LONG")]),
                cls.space.newtext("-T_C_LONG"),
                cls.space.newtext(
                    """
PyObject* raise_long(PyObject* module, PyObject* obj) {
  (void)module;
  long obj_int = PyLong_AsLong(obj);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = raise_long_impl(obj_int);
  return PyLong_FromLong(result);
}"""
                ),
                cls.space.newtext(
                    """
long raise_long_impl(long x) {
  if (x == 123) {
    PyErr_Format(PyExc_RuntimeError, "got 123. raising");
    return -1;
  }
  return x;
}"""
                ),
            ]
        )

    def test_import(self):
        module = self.import_module(name="signature")

    # long -> long

    def test_call_inc(self):
        module = self.make_module(self, *self.func_inc)
        result = module.inc(4)
        assert result == 5

    def test_call_inc_with_too_many_arguments_raises_type_error(self):
        module = self.make_module(self, *self.func_inc)
        with raises(TypeError) as info:
            module.inc(4, 5)
        assert str(info.value) == "inc() takes exactly one argument (2 given)", str(
            info.value
        )

    def test_call_inc_with_wrong_argument_type_raises_type_error(self):
        module = self.make_module(self, *self.func_inc)
        with raises(TypeError) as info:
            module.inc(4.5)
        assert str(info.value) == "expected integer, got float object", str(info.value)

    def test_call_inc_with_wrong_type_sig_raises_runtime_error(self):
        module = self.import_module(name="signature")
        with raises(RuntimeError) as info:
            module.wrong(1)
        assert (
            str(info.value) == "unreachable: unexpected METH_O|METH_TYPED signature"
        ), str(info.value)

    def test_call_long_does_not_raise(self):
        module = self.make_module(self, *self.func_raise_long)
        result = module.raise_long(8)
        assert result == 8

    def test_call_long_raises(self):
        module = self.make_module(self, *self.func_raise_long)
        with raises(RuntimeError) as info:
            module.raise_long(123)
        assert str(info.value) == "got 123. raising"

    # double -> double -> double

    def test_call_add(self):
        module = self.import_module(name="signature")
        result = module.add(1.0, 2.0)
        assert result == 3.0

    def test_call_add_with_too_many_arguments_raises_type_error(self):
        module = self.import_module(name="signature")
        with raises(TypeError) as info:
            module.add(4.0, 5.0, 6.0)
        assert str(info.value) == "add expected 2 arguments but got 3", str(info.value)

    def test_call_add_with_wrong_argument_type_raises_type_error(self):
        module = self.import_module(name="signature")
        with raises(TypeError) as info:
            module.add(4, 5)
        assert str(info.value) == "add expected float but got int", str(info.value)

    # double -> double

    def test_call_double_does_not_raise(self):
        module = self.import_module(name="signature")
        result = module.raise_double(1.0)
        assert result == 1.0

    def test_call_double_raises(self):
        module = self.import_module(name="signature")
        with raises(RuntimeError) as info:
            module.raise_double(0.0)
        assert str(info.value) == "got 0. raising"

    # PyObject -> long

    def test_call_pyobject_long_with_too_few_args_raises_type_error(self):
        module = self.import_module(name="signature")
        with raises(TypeError) as info:
            module.takes_object(1)
        assert str(info.value) == "takes_object expected 2 arguments but got 1", str(
            info.value
        )

    def test_call_pyobject_long_with_too_many_args_raises_type_error(self):
        module = self.import_module(name="signature")
        with raises(TypeError) as info:
            module.takes_object(1, 2, 3)
        assert str(info.value) == "takes_object expected 2 arguments but got 3", str(
            info.value
        )

    def test_call_pyobject_long_returns_int(self):
        module = self.import_module(name="signature")
        result = module.takes_object(object(), 8)
        assert result == 9, "%s %s" % (type(result), result)

    # PyObject -> PyObject

    def test_call_pyobject_with_too_few_args_raises_type_error(self):
        module = self.import_module(name="signature")
        with raises(TypeError) as info:
            module.takes_only_object()
        assert (
            str(info.value)
            == "takes_only_object() takes exactly one argument (0 given)"
        ), str(info.value)

    def test_call_pyobject_with_too_many_args_raises_type_error(self):
        module = self.import_module(name="signature")
        with raises(TypeError) as info:
            module.takes_only_object(1, 2)
        assert (
            str(info.value)
            == "takes_only_object() takes exactly one argument (2 given)"
        ), str(info.value)

    def test_call_pyobject_returns_same_object(self):
        module = self.import_module(name="signature")
        obj = object()
        result = module.takes_only_object(obj)
        assert result is obj
