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

PyPyTypedMethodMetadata inc_sig = {
  .arg_type = T_C_LONG,
  .ret_type = T_C_LONG,
  .underlying_func = inc_impl,
  .ml_name = "inc",
};

static PyMethodDef signature_methods[] = {
    {inc_sig.ml_name, inc, METH_O | METH_TYPED, "Add one to an int"},
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
  // TODO(max): Proper multi-phase
  return PyModule_Create(&signature_definition);
}
