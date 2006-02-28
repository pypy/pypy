
// python includes
#include <Python.h>
#include <structmember.h>

// llvm includes
#include "llvm/Type.h"
#include "llvm/Module.h"
#include "llvm/ModuleProvider.h"
#include "llvm/Assembly/Parser.h"
#include "llvm/Bytecode/Reader.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "llvm/Analysis/Verifier.h"

// c++ includes
#include <string>
#include <iostream>

using namespace llvm;

static PyObject *pyllvm_start_ee(PyObject *self, PyObject *args) {
  char *modulename, *llcode;

  if (!PyArg_ParseTuple(args, "ss", &modulename, &llcode)) {
    return NULL;
  }

  try {
    Module *mod = new Module((const char *) modulename);
    ModuleProvider *mp = new ExistingModuleProvider(mod);
    ParseAssemblyString((const char *) llcode, mod);// throw (ParseException)
    verifyModule(*mod, ThrowExceptionAction);
    ExecutionEngine *exec = ExecutionEngine::create(mp, false);
    assert(exec && "Couldn't create an ExecutionEngine, not even an interpreter?");
    delete exec;
  } catch (...) {
    PyErr_SetString(PyExc_Exception, "Unexpected unknown exception occurred");
    return NULL;
  }

  Py_INCREF(Py_None);
  return Py_None;
}

PyMethodDef pyllvm_functions[] = {
  {"start_ee", pyllvm_start_ee, METH_VARARGS, NULL},
  {NULL, NULL}
};


#ifdef __cplusplus
extern "C" {
#endif

void initpyllvm(void) {
  Py_InitModule("pyllvm", pyllvm_functions);

}

}
