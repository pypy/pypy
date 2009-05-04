/* LLVM includes */
#include <cstdio>
#include "llvm-c/ExecutionEngine.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "llvm/Target/TargetOptions.h"
#include "demo2.h"

using namespace llvm;


/* Set the flag to true.
 */
void _LLVM_SetFlags(void)
{
  PerformTailCallOpt = true;
}

/* This piece of code regroups conveniently a part of the initialization.
 */
LLVMExecutionEngineRef _LLVM_EE_Create(LLVMModuleRef M)
{
  LLVMModuleProviderRef mp = LLVMCreateModuleProviderForExistingModule(M);
  LLVMExecutionEngineRef ee;
  char* errormsg;
  int error = LLVMCreateJITCompiler(&ee, mp, 0 /*Fast*/, &errormsg);
  if (error)
    {
      fprintf(stderr, "Error creating the JIT compiler:\n%s", errormsg);
      abort();
    }
  return ee;
}

/* Missing pieces of the C interface...
 */
void *_LLVM_EE_getPointerToFunction(LLVMExecutionEngineRef EE,
                                    LLVMValueRef F)
{
  return unwrap(EE)->getPointerToFunction(unwrap<Function>(F));
}
