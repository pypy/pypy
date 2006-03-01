
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

static int from_python_to_args(std::vector<GenericValue> &llvmargs,
				PyObject *value,
				const Type *type) {
  // XXX Flesh out
  GenericValue res;
  if (type->getTypeID() == Type::IntTyID) {
    if (!PyInt_Check(value)) {
      PyErr_SetString(PyExc_TypeError, "expected an integer type");
      return -1;
    }
    res.IntVal = PyInt_AsLong(value);
    llvmargs.push_back(res);
    return 0;
  }

  std::string err = "unsupported type: " + type->getDescription();
  PyErr_SetString(PyExc_TypeError, err.c_str());
  return -1;
}

static PyObject *to_python_value(const GenericValue &value,
				 const Type *type) {

  // special case for strings - it is your own fault if not NULL terminated
  if (type->getTypeID() == Type::PointerTyID &&
      type->getContainedType(0)->getTypeID() == Type::SByteTyID) {
    return PyString_FromString((const char *) value.PointerVal);
  }

  PyObject *res;

  switch (type->getTypeID()) {

    case Type::VoidTyID:
      Py_INCREF(Py_None);
      res = Py_None;
      break;

    case Type::BoolTyID:
      res = PyBool_FromLong((long) value.BoolVal);
      break;

    case Type::UByteTyID:
      res = PyInt_FromLong((long) value.UByteVal);
      break;

    case Type::SByteTyID:
      res = PyInt_FromLong((long) value.SByteVal);
      break;

    case Type::UShortTyID:
      res = PyInt_FromLong((long) value.UShortVal);
      break;

    case Type::ShortTyID:
      res = PyInt_FromLong((long) value.ShortVal);
      break;

    case Type::UIntTyID:
      res = PyLong_FromUnsignedLong(value.UIntVal);
      break;

    case Type::IntTyID:
      res = PyInt_FromLong(value.IntVal);
      break;

    case Type::ULongTyID:
      res = PyLong_FromUnsignedLongLong((unsigned PY_LONG_LONG) value.ULongVal);
      break;

    case Type::LongTyID:
      res = PyLong_FromLongLong((PY_LONG_LONG) value.ULongVal);
      break;

      // XXX the rest
    default:
      std::string err = "unsupported type: " + type->getDescription();
      PyErr_SetString(PyExc_TypeError, err.c_str());
      res = NULL;
  }

  return res;
}

static PyObject *ee_call(PyExecutionEngine *self, PyObject *args) {

  if (PyTuple_Size(args) == 0) {
    PyErr_SetString(PyExc_TypeError, "first arg expected as string");
    return NULL;
  }

  PyObject *pyfnname = PyTuple_GetItem(args, 0); 
  if (!PyString_Check(pyfnname)) {
    PyErr_SetString(PyExc_TypeError, "first arg expected as string");
    return NULL;
  }

  char *fnname = PyString_AsString(pyfnname);
    
  try {
    Function *fn = self->exec->getModule().getNamedFunction(std::string(fnname));
    if (fn == NULL) {
      PyErr_SetString(PyExc_Exception, "Failed to resolve function");
      return NULL;
    }

    unsigned argcount = fn->getFunctionType()->getNumParams();
    if ((unsigned) PyTuple_Size(args) != argcount + 1) {
      PyErr_SetString(PyExc_TypeError, "args not much count");
      return NULL;
    }

    std::vector<GenericValue> llvmargs;
    for (unsigned ii=0; ii<argcount; ii++) {
      if (from_python_to_args(llvmargs,
			      PyTuple_GetItem(args, ii+1),
			      fn->getFunctionType()->getParamType(ii)) == -1) {
	return NULL;
      }
    }

    GenericValue ret = self->exec->runFunction(fn, llvmargs);
    return to_python_value(ret, fn->getFunctionType()->getReturnType());

  } catch (...) {
    PyErr_SetString(PyExc_Exception, "Unexpected unknown exception occurred");
    return NULL;
  }
}

static PyObject *ee_functions(PyExecutionEngine *self) {
  int funccount = 0;
  Module::FunctionListType &fns = self->exec->getModule().getFunctionList();
  // spin thrru and get function count 
  for (Module::FunctionListType::const_iterator ii = fns.begin(); ii != fns.end(); ++ii) {
    if (!(ii->isIntrinsic() || ii->isExternal())) {
      funccount += 1;
    }
  }    

  PyObject *functions = PyTuple_New(funccount);

  int count = 0;
  for (Module::FunctionListType::const_iterator ii = fns.begin(); 
       ii != fns.end(); 
       ++ii, funccount++) {
    if (!(ii->isIntrinsic() || ii->isExternal())) {

      unsigned argcount = ii->getFunctionType()->getNumParams();

      PyObject *entry = PyTuple_New(3);

      PyObject *returnId = PyInt_FromLong(ii->getFunctionType()->getReturnType()->getTypeID());
      PyObject *name = PyString_FromString(ii->getName().c_str());
      PyObject *args = PyTuple_New(argcount);

      for (unsigned jj=0; jj<argcount; jj++) {
	long argtype = ii->getFunctionType()->getParamType(jj)->getTypeID();
	PyTuple_SetItem(args, (long) jj, PyInt_FromLong(argtype));
      }
      
      PyTuple_SetItem(entry, 0, returnId);
      PyTuple_SetItem(entry, 1, name);
      PyTuple_SetItem(entry, 2, args);
      
      PyTuple_SetItem(functions, count, entry);
      count += 1;
    }
  }    
  
  return functions;
}

static PyMethodDef ee_methodlist[] = {
  {"parse", (PyCFunction) ee_parse, METH_VARARGS, NULL},
  {"functions", (PyCFunction) ee_functions, METH_NOARGS, NULL},
  {"call", (PyCFunction) ee_call, METH_VARARGS, NULL},

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
  PyExecutionEngine *ee = (PyExecutionEngine *) pyllvm_execution_engine;
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
