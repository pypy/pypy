#include <llvm-c/Core.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C"{
#endif
    LLVMTypeRef getResultElementType_wrapper(LLVMValueRef gep_instr);

    LLVMValueRef removeIncomingValue_wrapper(LLVMValueRef phi, LLVMBasicBlockRef block);

    void removePredecessor_wrapper(LLVMBasicBlockRef current, LLVMBasicBlockRef pred);

    LLVMValueRef getFirstNonPhi_wrapper(LLVMBasicBlockRef block);

    LLVMBasicBlockRef splitBasicBlockAtPhi_wrapper(LLVMBasicBlockRef block);

    LLVMValueRef getTerminator_wrapper(LLVMBasicBlockRef block);

    void dumpModule_wrapper(LLVMModuleRef mod);

    void dumpBasicBlock_wrapper(LLVMBasicBlockRef block);

    LLVMValueRef getIncomingValueForBlock_wrapper(LLVMValueRef phi, LLVMBasicBlockRef block);
#ifdef __cplusplus
}
#endif
