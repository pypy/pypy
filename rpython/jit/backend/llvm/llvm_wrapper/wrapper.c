#include "wrapper.h"
#include "wrapper_cpp.h"

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
	return LLVMVerifyModule(module, LLVMPrintMessageAction, &error);
}

void AddIncoming(LLVMValueRef phi, LLVMValueRef val, LLVMBasicBlockRef block){
	LLVMAddIncoming(phi, &val, &block, 1);
}

long GetSizeOf(LLVMTypeRef typ){
	LLVMValueRef size_llvm = LLVMSizeOf(typ);
	char *size_str = LLVMPrintValueToString(size_llvm);
	long size = atol(size_str);
	LLVMDisposeMessage(size_str);
	return size;
}

void SetJITEnums(struct JITEnums *enums){
	enums->codegenlevel = LLVMCodeGenLevelAggressive;
	enums->reloc = LLVMRelocDefault;
	enums->codemodel = LLVMCodeModelJITDefault;
}

void SetCmpEnums(struct CmpEnums *enums){
	enums->inteq = LLVMIntEQ;
	enums->intne = LLVMIntNE;
	enums->intugt = LLVMIntUGT;
	enums->intuge = LLVMIntUGE;
	enums->intult = LLVMIntULT;
	enums->intule = LLVMIntULE;
	enums->intsgt = LLVMIntSGT;
	enums->intsge = LLVMIntSGE;
	enums->intslt = LLVMIntSLT;
	enums->intsle = LLVMIntSLE;
	enums->realeq = LLVMRealOEQ;
	enums->realne = LLVMRealONE;
	enums->realgt = LLVMRealOGT;
	enums->realge = LLVMRealOGE;
	enums->reallt = LLVMRealOLT;
	enums->realle = LLVMRealOLE;
	enums->realord = LLVMRealORD;
}

LLVMTypeRef getResultElementType(LLVMValueRef gep_instr){
	return getResultElementType_wrapper(gep_instr);
}

LLVMValueRef removeIncomingValue(LLVMValueRef phi, LLVMBasicBlockRef block){
	return removeIncomingValue_wrapper(phi, block);
}

void removePredecessor(LLVMBasicBlockRef current, LLVMBasicBlockRef pred){
	removePredecessor_wrapper(current, pred);
}

LLVMValueRef getFirstNonPhi(LLVMBasicBlockRef block){
	return getFirstNonPhi_wrapper(block);
}

LLVMBasicBlockRef splitBasicBlockAtPhi(LLVMBasicBlockRef block){
	return splitBasicBlockAtPhi_wrapper(block);
}

LLVMValueRef getTerminator(LLVMBasicBlockRef block){
	return getTerminator_wrapper(block);
}

void dumpModule(LLVMModuleRef mod){
	dumpModule_wrapper(mod);
}

void dumpBasicBlock(LLVMBasicBlockRef block){
	dumpBasicBlock_wrapper(block);
}

LLVMValueRef getIncomingValueForBlock(LLVMValueRef phi, LLVMBasicBlockRef block){
	return getIncomingValueForBlock_wrapper(phi, block);
}

LLVMMCJITMemoryManagerRef CustomMemoryManager(void *Ctx){
	return LLVMCreateSimpleMCJITMemoryManager(Ctx,
											  )
}

LLVMOrcObjectLayerRef ObjectLinkingLayerCreator(void *Ctx, LLVMOrcExecutionSessionRef ES,
												const char *Triple){
	return LLVMOrcCreate
}
