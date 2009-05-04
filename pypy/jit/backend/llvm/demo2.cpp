/* LLVM includes */
#include "llvm-c/ExecutionEngine.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "demo2.h"

using namespace llvm;


/* Missing pieces of the C interface...
 */
void *_LLVM_EE_getPointerToFunction(LLVMExecutionEngineRef EE,
                                   LLVMValueRef F)
{
  return unwrap(EE)->getPointerToFunction(unwrap<Function>(F));
}
