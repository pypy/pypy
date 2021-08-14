#include "wrapper.h"
#include "wrapper_cpp.h"
#include <bits/types.h>

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
	enums->uno = LLVMRealUNO;
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

void create_breakpoint(){
	asm volatile (
		"int $3\n"
	);
}

void add_function_attribute(LLVMValueRef func, char *attribute, unsigned strlen,
							LLVMContextRef ctx){
	unsigned val = LLVMGetEnumAttributeKindForName(attribute, strlen);
	LLVMAttributeRef attr = LLVMCreateEnumAttribute(ctx, val, 0);
	LLVMAddAttributeAtIndex(func, LLVMAttributeFunctionIndex, attr);
}

void add_function_string_attribute(LLVMValueRef func, char *key, char *value,
								   LLVMContextRef ctx){
	unsigned key_len = (unsigned)strlen(key);
	unsigned value_len = (unsigned)strlen(value);

	LLVMAttributeRef attr = LLVMCreateStringAttribute(ctx, key, key_len, value,
													  value_len);
	LLVMAddAttributeAtIndex(func, LLVMAttributeFunctionIndex, attr);
}

//below code uses LLVM 13
/* uint8_t *allocate_code_section_callback(void *Opaque, uintptr_t Size, unsigned Alignment, unsigned SectionID, const char *SectionName){ */
/* 	return 0; */
/* } */

/* uint8_t *data_section_callback(void *Opaque, uintptr_t Size, unsigned Alingment, unsigned SectionID, const char *SectionName, LLVMBool IsReadOnly){ */
/* 	printf("%s\n", SectionName); */
/* 	return 0; */
/* } */

/* LLVMBool finalize_memory_callback(void *Opaque, char **ErrMsg){ */
/* 	return 0; */
/* } */

/* void memory_manager_destroy_callback(void *Opaque){ */
/* 	//TODO: this is probably where you should refresh JIT objects */
/* 	struct Ctx *ctx = (struct Ctx *)Opaque; */
/* 	int i; */
/* 	void *addr; */

/* 	for (i=0; i < ctx->section_count; i++){ */
/* 		addr = ctx->section_addrs[i]; */
/* 		size = ctx->section_sizes[i]; */
/* 		munmap(addr, size); */
/* 	} */

/* 	LLVMDisposeMCJITMemoryManager(ctx->memory_manager); */
/* } */

/* LLVMMCJITMemoryManagerRef memory_manager(void *Opaque){ */
/* 	LLVMMCJITMemoryManager MM = LLVMCreateSimpleMCJITMemoryManager(Opaque, */
/* 																   allocate_code_section_callback, */
/* 																   data_section_callback, */
/* 																   finalize_memory_callback, */
/* 																   memory_manager_destroy_callback); */
/* 	struct Ctx *ctx = (struct Ctx *)Opaque; */
/* 	ctx->memory_manager = MM; */
/* 	ctx->section_count = 0; */
/* 	ctx->section_addrs = calloc(64, sizeof(uint8_t *)); */
/* 	ctx->section_sizes = calloc(64, sizeof(size_t)); */
/* 	return MM; */
/* } */

/* LLVMOrcObjectLayerRef create_linking_layer(void *Opaque, LLVMOrcExecutionSessionRef ES, const char *Triple){ */
/* 	return LLVMOrcCreateRTDyldObjectLinkingLayer(ES, memory_manager, Opaque); */
/* } */

/* size_t parse_stackmap(unsigned index, Stackmap *stackmap){ */
/* 	Stackmap location = stackmap[index]; */

/* 	switch (location.type){ */
/* 		case 1: */

/* 	} */
/* } */
