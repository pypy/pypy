
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
#include "llvm/DerivedTypes.h"

// c++ includes
#include <string>
#include <iostream>

using namespace llvm;

typedef struct {
  PyObject_HEAD
  ExecutionEngine *exec;

} PyExecutionEngine;


static PyObject *ee_parse(PyExecutionEngine *self, PyObject *args) {
  char *llcode;

  if (!PyArg_ParseTuple(args, "s", &llcode)) {
    return NULL;
  }

  try {
    ParseAssemblyString((const char *) llcode, &self->exec->getModule());
    verifyModule(self->exec->getModule(), ThrowExceptionAction);
    Py_INCREF(Py_None);
    return Py_None;

  } catch (const ParseException &ref) {
    PyErr_SetString(PyExc_Exception, ref.getMessage().c_str());

  } catch (...) {
    PyErr_SetString(PyExc_Exception, "Unexpected unknown exception occurred");
  }

  return NULL;
}

static PyObject *ee_call_noargs(PyExecutionEngine *self, PyObject *args) {

  char *fnname;

  if (!PyArg_ParseTuple(args, "s", &fnname)) {
    return NULL;
  }
  
  try {
    Function *fn = self->exec->getModule().getNamedFunction(std::string(fnname));
    if (fn == NULL) {
      PyErr_SetString(PyExc_Exception, "Failed to resolve function");
      return NULL;
    }

    if (!fn->arg_empty()) {
      PyErr_SetString(PyExc_Exception, "Resolved function must take no args");
      return NULL;
    }    

    std::vector<GenericValue> noargs(0);
    GenericValue ret = self->exec->runFunction(fn, noargs);
  
  } catch (...) {
    PyErr_SetString(PyExc_Exception, "Unexpected unknown exception occurred");
    return NULL;
  }

  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject *ee_functions(PyExecutionEngine *self, PyObject *args) {

  Module::FunctionListType &fns = self->exec->getModule().getFunctionList();
  for (Module::FunctionListType::const_iterator ii = fns.begin(); ii != fns.end(); ++ii) {
    if (ii->isIntrinsic() || ii->isExternal()) {
      continue;
    }
    std::cout << ii->getReturnType()->getDescription() << " " << ii->getName() << std::endl;
    std::cout << "   -> " << ii->getFunctionType()->getDescription() << std::endl;
    std::cout << std::endl;
  }
  
  Py_INCREF(Py_None);
  return Py_None;
}

static PyMethodDef ee_methodlist[] = {
  {"parse", (PyCFunction) ee_parse, METH_VARARGS, NULL},
  {"functions", (PyCFunction) ee_functions, METH_NOARGS, NULL},
  {"call_noargs", (PyCFunction) ee_call_noargs, METH_VARARGS, NULL},

  {NULL, NULL}
};

void ee_dealloc(PyExecutionEngine *self);
PyObject *ee_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

// PyTypeObject - pythons type structure
PyTypeObject ExecutionEngine_Type = {
  PyObject_HEAD_INIT(NULL)
  0,
  "ExecutionEngine",
  sizeof(PyExecutionEngine),
  0,
  (destructor)ee_dealloc,                   /* tp_dealloc */
  0,                                        /* tp_print */
  0,                                        /* tp_getattr */
  0,                                        /* tp_setattr */
  0,                                        /* tp_compare */
  0,                                        /* tp_repr */
  0,                                        /* tp_as_number */
  0,                                        /* tp_as_sequence */
  0,                                        /* tp_as_mapping */
  0,                                        /* tp_hash */
  0,                                        /* tp_call */
  0,                                        /* tp_str */
  0,                                        /* tp_getattro */
  0,                                        /* tp_setattro */
  0,                                        /* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,                       /* tp_flags */
  0,                                        /* tp_doc */
  0,                                        /* tp_traverse */
  0,                                        /* tp_clear */
  0,                                        /* tp_richcompare */
  0,                                        /* tp_weaklistoffset */
  0,                                        /* tp_iter */
  0,                                        /* tp_iternext */
  ee_methodlist,                            /* tp_methods */
  0,                                        /* tp_members */
  0,                                        /* tp_getset */
  0,                                        /* tp_base */
  0,                                        /* tp_dict */
  0,                                        /* tp_descr_get */
  0,                                        /* tp_descr_set */
  0,                                        /* tp_dictoffset */
  0,                                        /* tp_init */
  0,                                        /* tp_alloc */
  0,                                        /* tp_new */
};

PyObject *pyllvm_execution_engine;

static PyObject *ee_factory() {

  if (pyllvm_execution_engine != NULL) {
    PyErr_SetString(PyExc_Exception, "This should not happen");
    return NULL;
  }

  ExecutionEngine *exec;

  try {
    Module *mod = new Module((const char *) "my module");
    ModuleProvider *mp = new ExistingModuleProvider(mod);
    exec = ExecutionEngine::create(mp, false);
    assert(exec && "Couldn't create an ExecutionEngine, not even an interpreter?");
  } catch (...) {
    PyErr_SetString(PyExc_Exception, "Unexpected unknown exception occurred");
    return NULL;
  }

  PyTypeObject *type = &ExecutionEngine_Type;

  PyExecutionEngine *self = (PyExecutionEngine *) type->tp_alloc(type, 0);
  self->exec = exec;

  return (PyObject *) self;
}

void ee_dealloc(PyExecutionEngine *self) {
  // next and prev taken care of by append/remove/dealloc in dlist
  self->ob_type->tp_free((PyObject*) self);
}

static PyObject *pyllvm_get_ee(PyObject *self, PyObject *args) {
  if (pyllvm_execution_engine != NULL) {
    Py_INCREF(pyllvm_execution_engine);
    return pyllvm_execution_engine;
  }

  pyllvm_execution_engine = ee_factory();
  return pyllvm_execution_engine;
}

static PyObject *pyllvm_delete_ee(PyObject *self, PyObject *args) {
  PyExecutionEngine *ee =  (PyExecutionEngine *) pyllvm_execution_engine;
  if (ee != NULL) {

    // bye
    if (ee->exec != NULL) {
      delete ee->exec;
    }
   
    Py_DECREF(pyllvm_execution_engine);
    pyllvm_execution_engine = NULL;
  }
  
  Py_INCREF(Py_None);
  return Py_None;
}

PyMethodDef pyllvm_functions[] = {
  {"get_ee", pyllvm_get_ee, METH_NOARGS, NULL},
  {"delete_ee", pyllvm_delete_ee, METH_NOARGS, NULL},
  {NULL, NULL}
};


#ifdef __cplusplus
extern "C" {
#endif

void initpyllvm(void) {
  PyObject *module = Py_InitModule("pyllvm", pyllvm_functions);

  if(PyType_Ready(&ExecutionEngine_Type) < 0) {
    return;
  }

  Py_INCREF(&ExecutionEngine_Type);
  PyModule_AddObject(module, "ExecutionEngine", 
		     (PyObject*) &ExecutionEngine_Type);

}

}
