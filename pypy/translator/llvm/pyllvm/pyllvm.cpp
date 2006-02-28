
#include <Python.h>
#include <structmember.h>

#include "llvm/Module.h"
#include "llvm/ModuleProvider.h"
#include "llvm/Type.h"
#include "llvm/Bytecode/Reader.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/PluginLoader.h"
#include "llvm/System/Signals.h"
#include "llvm/Assembly/Parser.h"
#include "llvm/Analysis/Verifier.h"
#include <string>
#include <iostream>

using namespace llvm;

static PyObject *pyllvm_start_ee(PyObject *self, PyObject *args) {
  char *modulename, *llcode;

  if (!PyArg_ParseTuple(args, "ss", &modulename, &llcode)) {
    return NULL;
  }

  int Result = -1;

  try {
    printf("here1\n");
    Module *mod = new Module((const char *) modulename);
    printf("here2\n");

    ModuleProvider *mp = new ExistingModuleProvider(mod);
    printf("here3\n");
    ParseAssemblyString((const char *) llcode, mod);// throw (ParseException)
    printf("here4\n");
    verifyModule(*mod, ThrowExceptionAction);
    printf("here5\n");
    ExecutionEngine *exec = ExecutionEngine::create(mp, false);
    printf("here6\n");
    assert(exec && "Couldn't create an ExecutionEngine, not even an interpreter?");
    printf("here7\n");
    delete exec;
    printf("here8\n");

//     delete mp;
//     printf("here9\n");
//     delete mod;
//     printf("here10\n");

//     // Call the main function from M as if its signature were:
//     //   int main (int argc, char **argv, const char **envp)
//     // using the contents of Args to determine argc & argv, and the contents of
//     // EnvVars to determine envp.
//     //
//     Function *Fn = MP->getModule()->getMainFunction();
//     if (!Fn) {
//       std::cerr << "'main' function not found in module.\n";
//       return -1;
//     }

//     // Run main...
//     int Result = EE->runFunctionAsMain(Fn, InputArgv, envp);

//     // If the program didn't explicitly call exit, call exit now, for the program.
//     // This ensures that any atexit handlers get called correctly.
//     Function *Exit = MP->getModule()->getOrInsertFunction("exit", Type::VoidTy,
//                                                           Type::IntTy,
//                                                           (Type *)0);

//     std::vector<GenericValue> Args;
//     GenericValue ResultGV;
//     ResultGV.IntVal = Result;
//     Args.push_back(ResultGV);
//     EE->runFunction(Exit, Args);

    std::cerr << "ERROR: exit(" << Result << ") returned!\n";
  } catch (const std::string& msg) {
    std::cerr << ": " << msg << "\n";
  } catch (...) {
    std::cerr << ": Unexpected unknown exception occurred.\n";
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
  PyObject *pyllvm = Py_InitModule("pyllvm", pyllvm_functions);

}

} // __cplusplus
