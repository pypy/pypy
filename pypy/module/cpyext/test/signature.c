#include <Python.h>

long inc_impl(long arg) {
  return arg+1;
}

PyObject* inc(PyObject* module, PyObject* obj) {
  (void)module;
  long obj_int = PyLong_AsLong(obj);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = inc_impl(obj_int);
  return PyLong_FromLong(result);
}

int inc_arg_types[] = {T_C_LONG, -1};

PyPyTypedMethodMetadata inc_sig = {
  .arg_types = inc_arg_types,
  .ret_type = T_C_LONG,
  .underlying_func = inc_impl,
  .ml_name = "inc",
};

int wrong_arg_types[] = {100, -1};

PyPyTypedMethodMetadata wrong_sig = {
  .arg_types = wrong_arg_types,
  .ret_type = T_C_LONG,
  .underlying_func = inc_impl,
  .ml_name = "wrong",
};

double add_impl(double left, double right) {
  return left + right;
}

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
}

int add_arg_types[] = {T_C_DOUBLE, T_C_DOUBLE, -1};

PyPyTypedMethodMetadata add_sig = {
  .arg_types = add_arg_types,
  .ret_type = T_C_DOUBLE,
  .underlying_func = add_impl,
  .ml_name = "add",
};

long raise_long_impl(long x) {
  if (x == 123) {
    PyErr_Format(PyExc_RuntimeError, "got 123. raising");
    return -1;
  }
  return x;
}

PyObject* raise_long(PyObject* module, PyObject* obj) {
  (void)module;
  long obj_int = PyLong_AsLong(obj);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = raise_long_impl(obj_int);
  if (result == -1 && PyErr_Occurred()) {
    return NULL;
  }
  return PyLong_FromLong(result);
}

int raise_long_arg_types[] = {T_C_LONG, -1};

PyPyTypedMethodMetadata raise_long_sig = {
  .arg_types = raise_long_arg_types,
  .ret_type = -T_C_LONG,
  .underlying_func = raise_long_impl,
  .ml_name = "raise_long",
};

double raise_double_impl(double x) {
  if (x == 0.0) {
    PyErr_Format(PyExc_RuntimeError, "got 0. raising");
    return -0.0;
  }
  return x;
}

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
}

int raise_double_arg_types[] = {T_C_DOUBLE, -1};

PyPyTypedMethodMetadata raise_double_sig = {
  .arg_types = raise_double_arg_types,
  .ret_type = -T_C_DOUBLE,
  .underlying_func = raise_double_impl,
  .ml_name = "raise_double",
};

long takes_object_impl(PyObject* obj, long arg) {
  (void)obj;
  return arg + 1;
}

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
}

int takes_object_arg_types[] = {T_PY_OBJECT, T_C_LONG, -1};

PyPyTypedMethodMetadata takes_object_sig = {
  .arg_types = takes_object_arg_types,
  .ret_type = T_C_LONG,
  .underlying_func = takes_object_impl,
  .ml_name = "takes_object",
};

static PyMethodDef signature_methods[] = {
    {inc_sig.ml_name, inc, METH_O | METH_TYPED, "Add one to an int"},
    {wrong_sig.ml_name, inc, METH_O | METH_TYPED, "Have a silly signature"},
    {add_sig.ml_name, (PyCFunction)(void*)add, METH_FASTCALL | METH_TYPED, "Add two doubles"},
    {raise_long_sig.ml_name, raise_long, METH_O | METH_TYPED, "Raise an exception (long)"},
    {raise_double_sig.ml_name, raise_double, METH_O | METH_TYPED, "Raise an exception (double)"},
    {takes_object_sig.ml_name, (PyCFunction)(void*)takes_object, METH_FASTCALL | METH_TYPED, "Inc but also takes a PyObject*"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef signature_definition = {
    PyModuleDef_HEAD_INIT, "signature",
    "A C extension module with type information exposed.", -1,
    signature_methods,
    NULL,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit_signature(void) {
  PyObject* result = PyState_FindModule(&signature_definition);
  if (result != NULL) {
    return Py_NewRef(result);
  }
  return PyModule_Create(&signature_definition);
}
