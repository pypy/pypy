#include <Python.h>

long wrong_impl(long arg) {
  return arg+1;
}

PyObject* wrong(PyObject* module, PyObject* obj) {
  (void)module;
  long obj_int = PyLong_AsLong(obj);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = wrong_impl(obj_int);
  return PyLong_FromLong(result);
}

int wrong_arg_types[] = {100, -1};

PyPyTypedMethodMetadata wrong_sig = {
  .arg_types = wrong_arg_types,
  .ret_type = T_C_LONG,
  .underlying_func = wrong_impl,
  .ml_name = "wrong",
};

static PyMethodDef signature_methods[] = {
    {wrong_sig.ml_name, wrong, METH_O | METH_TYPED, "Have a silly signature"},
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
