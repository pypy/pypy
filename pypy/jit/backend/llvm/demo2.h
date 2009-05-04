
#ifdef __cplusplus
extern "C" {
#endif
  
LLVMExecutionEngineRef _LLVM_EE_Create(LLVMModuleRef M);
void *_LLVM_EE_getPointerToFunction(LLVMExecutionEngineRef EE,
                                    LLVMValueRef F);

#ifdef __cplusplus
}
#endif
