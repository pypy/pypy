
#ifdef __cplusplus
extern "C" {
#endif

void _LLVM_SetFlags(void);
LLVMExecutionEngineRef _LLVM_EE_Create(LLVMModuleRef M);
void *_LLVM_EE_getPointerToFunction(LLVMExecutionEngineRef EE,
                                    LLVMValueRef F);
LLVMValueRef _LLVM_Intrinsic_add_ovf(LLVMModuleRef M, LLVMTypeRef Ty);
LLVMValueRef _LLVM_Intrinsic_sub_ovf(LLVMModuleRef M, LLVMTypeRef Ty);
LLVMValueRef _LLVM_Intrinsic_mul_ovf(LLVMModuleRef M, LLVMTypeRef Ty);

#ifdef __cplusplus
}
#endif
