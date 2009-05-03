/* LLVM includes */
#include "llvm-c/Analysis.h"
#include "llvm-c/Transforms/Scalar.h"
#include "llvm-c/ExecutionEngine.h"

/* The following list of functions seems to be necessary to force the
 * functions to be included in pypy_cache_llvm.so.  The list is never
 * used.
 */
void* llvm_c_functions[] = {
  (void*) LLVMModuleCreateWithName
};
