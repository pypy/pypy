/* LLVM includes */
#include <cstdio>
#include "llvm-c/ExecutionEngine.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "demo2.h"

using namespace llvm;


/* Missing pieces of the C interface...
 */
LLVMExecutionEngineRef _LLVM_EE_Create(LLVMModuleRef M)
{
  LLVMModuleProviderRef mp = LLVMCreateModuleProviderForExistingModule(M);
  LLVMExecutionEngineRef ee;
  char* errormsg;
  int error = LLVMCreateJITCompiler(&ee, mp, 1 /*Fast*/, &errormsg);
  if (error)
    {
      fprintf(stderr, "Error creating the JIT compiler:\n%s", errormsg);
      abort();
    }
  return ee;
}

void *_LLVM_EE_getPointerToFunction(LLVMExecutionEngineRef EE,
                                    LLVMValueRef F)
{
  return unwrap(EE)->getPointerToFunction(unwrap<Function>(F));
}
