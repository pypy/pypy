/* LLVM includes */
#include "llvm-c/Analysis.h"
#include "llvm-c/Transforms/Scalar.h"
#include "llvm-c/ExecutionEngine.h"
#include "demo2.h"

/* The following list of functions seems to be necessary to force the
 * functions to be included in pypy_cache_llvm.so.  The list is never
 * used.  Actually, any single function seems to be enough...
 */
void* llvm_c_functions[] = {
  (void*) LLVMModuleCreateWithName,
  (void*) _LLVM_EE_getPointerToFunction,
  (void*) _LLVM_Intrinsic_add_ovf,
  (void*) _LLVM_Intrinsic_sub_ovf,
  (void*) _LLVM_Intrinsic_mul_ovf
};
