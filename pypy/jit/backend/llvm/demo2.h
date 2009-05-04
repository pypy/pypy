#ifdef __cplusplus
extern "C" {
#endif

void* _LLVM_EE_getPointerToFunction(LLVMExecutionEngineRef EE,
                                    LLVMValueRef F);

#ifdef __cplusplus
}
#endif
