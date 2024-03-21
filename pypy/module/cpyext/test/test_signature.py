from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestSignature(AppTestCpythonExtensionBase):
    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)
        cls.w_make_module = cls.space.appexec(
            [],
            '''():
            def make_module(self, name, arg_types, ret_type, wrapper, impl):
                if len(arg_types) == 0:
                    arg_types_str = ""
                    flags = "METH_NOARGS"
                elif len(arg_types) == 1:
                    arg_types_str = arg_types[0] + ", "
                    flags = "METH_O"
                else:
                    arg_types_str = ", ".join(arg_types) + ", "
                    flags = "METH_FASTCALL"
                body = """
                {0}
                {1}
                int {2}_arg_types[] = {{ {3} -1 }};
                PyPyTypedMethodMetadata {2}_sig = {{
                  .arg_types = {2}_arg_types,
                  .ret_type = {4},
                  .underlying_func = {2}_impl,
                #define STR(x) #x
                  .ml_name = STR({2}),
                }};
                static PyMethodDef signature_methods[] = {{
                    {{ {2}_sig.ml_name, (PyCFunction)({2}), {5} | METH_TYPED, STR({2}) }},
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
        cls.w_func_add = cls.space.newtuple(
            [
                cls.space.newtext("add"),
                cls.space.newtuple(
                    [cls.space.newtext("T_C_DOUBLE"), cls.space.newtext("T_C_DOUBLE")]
                ),
                cls.space.newtext("T_C_DOUBLE"),
                cls.space.newtext(
                    """
PyObject* add(PyObject* module, PyObject*const *args, Py_ssize_t nargs) {
  (void)module;
  if (nargs != 2) {
    return PyErr_Format(PyExc_TypeError, "add expected 2 arguments but got %ld", nargs);
  }
  if (!PyFloat_CheckExact(args[0])) {
    return PyErr_Format(PyExc_TypeError, "add expected float but got %s", Py_TYPE(args[0])->tp_name);
  }
  double left = PyFloat_AsDouble(args[0]);
  if (PyErr_Occurred()) return NULL;
  if (!PyFloat_CheckExact(args[1])) {
    return PyErr_Format(PyExc_TypeError, "add expected float but got %s", Py_TYPE(args[1])->tp_name);
  }
  double right = PyFloat_AsDouble(args[1]);
  if (PyErr_Occurred()) return NULL;
  double result = add_impl(left, right);
  return PyFloat_FromDouble(result);
}"""
                ),
                cls.space.newtext(
                    """
double add_impl(double left, double right) {
  return left + right;
}"""
                ),
            ]
        )
        cls.w_func_raise_double = cls.space.newtuple(
            [
                cls.space.newtext("raise_double"),
                cls.space.newtuple([cls.space.newtext("T_C_DOUBLE")]),
                cls.space.newtext("-T_C_DOUBLE"),
                cls.space.newtext(
                    """
PyObject* raise_double(PyObject* module, PyObject* obj) {
  (void)module;
  double obj_double = PyFloat_AsDouble(obj);
  if (obj_double == -1 && PyErr_Occurred()) {
    return NULL;
  }
  double result = raise_double_impl(obj_double);
  if (result == -1 && PyErr_Occurred()) {
    return NULL;
  }
  return PyFloat_FromDouble(result);
}"""
                ),
                cls.space.newtext(
                    """
double raise_double_impl(double x) {
  if (x == 0.0) {
    PyErr_Format(PyExc_RuntimeError, "got 0. raising");
    return -0.0;
  }
  return x;
}"""
                ),
            ]
        )
        cls.w_func_takes_object = cls.space.newtuple(
            [
                cls.space.newtext("takes_object"),
                cls.space.newtuple(
                    [cls.space.newtext("T_PY_OBJECT"), cls.space.newtext("T_C_LONG")]
                ),
                cls.space.newtext("T_C_LONG"),
                cls.space.newtext(
                    """
PyObject* takes_object(PyObject* module, PyObject*const *args, Py_ssize_t nargs) {
  (void)module;
  if (nargs != 2) {
    return PyErr_Format(PyExc_TypeError, "takes_object expected 2 arguments but got %ld", nargs);
  }
  PyObject* obj = args[0];
  assert(obj != NULL);
  long obj_int = PyLong_AsLong(args[1]);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = takes_object_impl(obj, obj_int);
  return PyLong_FromLong(result);
}"""
                ),
                cls.space.newtext(
                    """
long takes_object_impl(PyObject* obj, long arg) {
  (void)obj;
  return arg + 1;
}"""
                ),
            ]
        )
        cls.w_func_takes_only_object = cls.space.newtuple(
            [
                cls.space.newtext("takes_only_object"),
                cls.space.newtuple([cls.space.newtext("T_PY_OBJECT")]),
                cls.space.newtext("T_PY_OBJECT"),
                cls.space.newtext(
                    """
PyObject* takes_only_object(PyObject* module, PyObject* obj) {
  (void)module;
  return takes_only_object_impl(obj);
}"""
                ),
                cls.space.newtext(
                    """
PyObject* takes_only_object_impl(PyObject* arg) {
  Py_INCREF(arg);
  return arg;
}"""
                ),
            ]
        )
        cls.w_func_wrong = cls.space.newtuple(
            [
                cls.space.newtext("wrong"),
                # Some invalid type identifier
                cls.space.newtuple([cls.space.newtext("999")]),
                cls.space.newtext("T_C_LONG"),
                cls.space.newtext(
                    """
PyObject* wrong(PyObject* module, PyObject* obj) {
  (void)module;
  long obj_int = PyLong_AsLong(obj);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = wrong_impl(obj_int);
  return PyLong_FromLong(result);
}"""
                ),
                cls.space.newtext(
                    """
long wrong_impl(long arg) {
  return arg+1;
}"""
                ),
            ]
        )
        cls.w_func_muladd = cls.space.newtuple(
            [
                cls.space.newtext("muladd"),
                cls.space.newtuple(
                    [
                        cls.space.newtext("T_C_DOUBLE"),
                        cls.space.newtext("T_C_DOUBLE"),
                        cls.space.newtext("T_C_DOUBLE"),
                    ]
                ),
                cls.space.newtext("T_C_DOUBLE"),
                cls.space.newtext(
                    """
PyObject* muladd(PyObject* module, PyObject*const *args, Py_ssize_t nargs) {
  (void)module;
  if (nargs != 3) {
    return PyErr_Format(PyExc_TypeError, "muladd expected 3 arguments but got %ld", nargs);
  }
  if (!PyFloat_CheckExact(args[0])) {
    return PyErr_Format(PyExc_TypeError, "muladd expected float but got %s", Py_TYPE(args[0])->tp_name);
  }
  double a = PyFloat_AsDouble(args[0]);
  if (PyErr_Occurred()) return NULL;
  if (!PyFloat_CheckExact(args[1])) {
    return PyErr_Format(PyExc_TypeError, "muladd expected float but got %s", Py_TYPE(args[1])->tp_name);
  }
  double b = PyFloat_AsDouble(args[1]);
  if (!PyFloat_CheckExact(args[2])) {
    return PyErr_Format(PyExc_TypeError, "add expected float but got %s", Py_TYPE(args[2])->tp_name);
  }
  double c = PyFloat_AsDouble(args[2]);
  if (PyErr_Occurred()) return NULL;
  return PyFloat_FromDouble(muladd_impl(a, b, c));
}"""
                ),
                cls.space.newtext(
                    """
double muladd_impl(double a, double b, double c) {
  return a + b * c;
}"""
                ),
            ]
        )
        cls.w_func_does_have_gil_noargs = cls.space.newtuple(
            [
                cls.space.newtext("does_have_gil"),
                cls.space.newtuple([]),
                cls.space.newtext("T_C_LONG"),
                cls.space.newtext(
                    """
PyObject* does_have_gil(PyObject* module) {
    (void)module;
    return PyLong_FromLong(does_have_gil_impl());
}"""
                ),
                cls.space.newtext(
                    """
long does_have_gil_impl() {
  return PyGILState_Check();
}"""
                ),
            ]
        )

        cls.w_func_does_have_gil_o = cls.space.newtuple(
            [
                cls.space.newtext("does_have_gil"),
                cls.space.newtuple([cls.space.newtext("T_PY_OBJECT")]),
                cls.space.newtext("T_C_LONG"),
                cls.space.newtext(
                    """
PyObject* does_have_gil(PyObject* module, PyObject* obj) {
    (void)module;
    return PyLong_FromLong(does_have_gil_impl(obj));
}"""
                ),
                cls.space.newtext(
                    """
long does_have_gil_impl(PyObject* obj) {
  (void)obj;
  return PyGILState_Check();
}"""
                ),
            ]
        )

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

    def Xtest_call_inc_with_wrong_type_sig_raises_runtime_error(self):
        module = self.make_module(self, *self.func_wrong)
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
        module = self.make_module(self, *self.func_add)
        result = module.add(1.0, 2.0)
        assert result == 3.0

    def test_call_add_with_too_many_arguments_raises_type_error(self):
        module = self.make_module(self, *self.func_add)
        with raises(TypeError) as info:
            module.add(4.0, 5.0, 6.0)
        assert str(info.value) == "add expected 2 arguments but got 3", str(info.value)

    def test_call_add_with_wrong_argument_type_raises_type_error(self):
        module = self.make_module(self, *self.func_add)
        with raises(TypeError) as info:
            module.add(4, 5)
        assert str(info.value) == "add expected float but got int", str(info.value)

    # double -> double

    def test_call_double_does_not_raise(self):
        module = self.make_module(self, *self.func_raise_double)
        result = module.raise_double(1.0)
        assert result == 1.0

    def test_call_double_raises(self):
        module = self.make_module(self, *self.func_raise_double)
        with raises(RuntimeError) as info:
            module.raise_double(0.0)
        assert str(info.value) == "got 0. raising"

    # PyObject -> long

    def test_call_pyobject_long_with_too_few_args_raises_type_error(self):
        module = self.make_module(self, *self.func_takes_object)
        with raises(TypeError) as info:
            module.takes_object(1)
        assert str(info.value) == "takes_object expected 2 arguments but got 1", str(
            info.value
        )

    def test_call_pyobject_long_with_too_many_args_raises_type_error(self):
        module = self.make_module(self, *self.func_takes_object)
        with raises(TypeError) as info:
            module.takes_object(1, 2, 3)
        assert str(info.value) == "takes_object expected 2 arguments but got 3", str(
            info.value
        )

    def test_call_pyobject_long_returns_int(self):
        module = self.make_module(self, *self.func_takes_object)
        result = module.takes_object(object(), 8)
        assert result == 9, "%s %s" % (type(result), result)

    # PyObject -> PyObject

    def test_call_pyobject_with_too_few_args_raises_type_error(self):
        module = self.make_module(self, *self.func_takes_only_object)
        with raises(TypeError) as info:
            module.takes_only_object()
        assert (
            str(info.value)
            == "takes_only_object() takes exactly one argument (0 given)"
        ), str(info.value)

    def test_call_pyobject_with_too_many_args_raises_type_error(self):
        module = self.make_module(self, *self.func_takes_only_object)
        with raises(TypeError) as info:
            module.takes_only_object(1, 2)
        assert (
            str(info.value)
            == "takes_only_object() takes exactly one argument (2 given)"
        ), str(info.value)

    def test_call_pyobject_returns_same_object(self):
        module = self.make_module(self, *self.func_takes_only_object)
        obj = object()
        result = module.takes_only_object(obj)
        assert result is obj

    # double -> double -> double -> double

    def test_muladd(self):
        module = self.make_module(self, *self.func_muladd)
        assert module.muladd(1.0, 2.0, 3.0) == 1.0 + 2.0 * 3.0

    def test_gil_not_released_meth_o(self):
        module = self.make_module(self, *self.func_does_have_gil_o)
        had_gil = module.does_have_gil(None)
        assert had_gil

    def test_gil_not_released_meth_noargs(self):
        module = self.make_module(self, *self.func_does_have_gil_noargs)
        had_gil = module.does_have_gil()
        assert had_gil
