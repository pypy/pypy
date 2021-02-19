#include "wrapper.h"

LLVMBool InitializeNativeTarget(void)	{
	return LLVMInitializeNativeTarget();
}

LLVMBool InitializeNativeAsmPrinter(void)	{
	return LLVMInitializeNativeAsmPrinter();
}

LLVMBool InitializeNativeAsmParser(void)	{
	return LLVMInitializeNativeAsmParser();
}

LLVMTargetRef GetTargetFromTriple(const char* triple){
	char *error = NULL;
	LLVMTargetRef target;
	LLVMBool success =  LLVMGetTargetFromTriple(triple, &target, &error);
	if (success != 0){
		return target;
	}
	else {
		return NULL; //can add in a printf to display the error here for debugging if need be
	}
}

LLVMOrcLLJITRef CreateLLJIT(LLVMOrcLLJITBuilderRef builder){
	LLVMOrcLLJITRef jit;
	LLVMErrorRef success = LLVMOrcCreateLLJIT(&jit, builder);
	if (success == NULL){
		return jit;
	}
	else{
		return NULL
	}
}

LLVMOrcJITTargetAddress LLJITLookup(LLVMOrcLLJITRef jit, const char *name){
	LLVMOrcJITTargetAddress addr;
	LLVMErrorRef success = LLVMOrcLLJITLookup(jit, &addr, name);
	if (success == NULL){
		return addr;
	}
	else {
		return NULL;
	}
}

LLVMBool VerifyModule(LLVMModuleRef module, LLVMVerifierFailureAction action){
	char *error = NULL;
	return LLVMVerifyModule(module, action, &error);
}
