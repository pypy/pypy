#include "wrapper.h"

LLVMBool InitializeNativeTarget(void)	{
	return LLVMInitializeNativeTarget();
}

LLVMBool InitializeNativeAsmPrinter(void)	{
	return LLVMInitializeNativeAsmPrinter();
}

LLVMTargetRef GetTargetFromTriple(const char* triple){
	char *error = NULL;
	LLVMTargetRef target;
	LLVMBool success =  LLVMGetTargetFromTriple(triple, &target, &error);
	if (success == 0){
		return target;
	}
	else {
		return NULL; //can add in a printf to display the error here for debugging if need be
	}
}
LLVMErrorRef LLJITAddLLVMIRModule(LLVMOrcLLJITRef jit, LLVMOrcJITDylibRef dylib, LLVMOrcThreadSafeModuleRef module){
	return LLVMOrcLLJITAddLLVMIRModule(jit, dylib, module);
}

LLVMOrcLLJITRef CreateLLJIT(LLVMOrcLLJITBuilderRef builder){
	LLVMOrcLLJITRef jit;
	LLVMErrorRef success = LLVMOrcCreateLLJIT(&jit, builder);
	if (success == NULL){
		return jit;
	}
	else{
		return NULL;
	}
}

LLVMOrcJITTargetAddress LLJITLookup(LLVMOrcLLJITRef jit, const char *name){
	LLVMOrcJITTargetAddress addr;
	LLVMErrorRef success = LLVMOrcLLJITLookup(jit, &addr, name);
	if (success == NULL){
		return addr;
	}
	else {
		return 0; //JITTargetAddress is defined as uint64
	}
}

LLVMBool VerifyModule(LLVMModuleRef module){
	char *error = NULL;
	return LLVMVerifyModule(module, LLVMAbortProcessAction, &error);
}

void AddIncoming(LLVMValueRef phi, LLVMValueRef val, LLVMBasicBlockRef block){
	LLVMAddIncoming(phi, &val, &block, 1);
}

LLVMValueRef BuildICmp(LLVMBuilderRef builder, int op, LLVMValueRef lhs, LLVMValueRef rhs, char *name){
	LLVMIntPredicate pred;
	switch (op){ //hack because I couldn't be bothered to get enums working through the rffi for now
		case 1:
			pred = LLVMIntEQ;
			break;
		case 2:
			pred = LLVMIntNE;
			break;
		case 3:
			pred = LLVMIntUGT;
			break;
		case 4:
			pred = LLVMIntUGE;
			break;
		case 5:
			pred = LLVMIntULE;
			break;
		case 6:
			pred = LLVMIntSGT;
			break;
		case 7:
			pred = LLVMIntSGE;
			break;
		case 8:
			pred = LLVMIntSLT;
			break;
		case 9:
			pred = LLVMIntSLE;
			break;
	}
	return LLVMBuildICmp(builder, pred, lhs, rhs, name);
}

LLVMValueRef BuildGEP1D(LLVMBuilderRef builder, LLVMTypeRef typ, LLVMValueRef ptr, LLVMValueRef indx, char *name){
	return LLVMBuildGEP2(builder, typ, ptr, &indx, 1, name);
}

LLVMValueRef BuildGEP2D(LLVMBuilderRef builder, LLVMTypeRef typ, LLVMValueRef ptr, LLVMValueRef indx1, LLVMValueRef indx2, char *name){
	LLVMValueRef arr[] = {indx1, indx2};
	return LLVMBuildGEP2(builder, typ, ptr, arr, 2, name);
}

LLVMValueRef BuildGEP3D(LLVMBuilderRef builder, LLVMTypeRef typ, LLVMValueRef ptr, LLVMValueRef indx1, LLVMValueRef indx2, LLVMValueRef indx3, char *name){
	LLVMValueRef arr[] = {indx1, indx2, indx3};
	return LLVMBuildGEP2(builder, typ, ptr, arr, 3, name);
}
