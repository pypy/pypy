#pragma once

#include <llvm-c/Target.h>
#include <llvm-c/TargetMachine.h>
#include <llvm-c/Orc.h>
#include <llvm-c/OrcEE.h>
#include <llvm-c/Analysis.h>
#include <llvm-c/ExecutionEngine.h>
#include <llvm-c/Core.h>
#include <llvm-c/LLJIT.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/types.h>

LLVMBool InitializeNativeTarget(void);

LLVMBool InitializeNativeAsmPrinter(void);

LLVMTargetRef GetTargetFromTriple(const char* triple);

LLVMOrcLLJITRef CreateLLJIT(LLVMOrcLLJITBuilderRef builder);

LLVMErrorRef LLJITAddLLVMIRModule(LLVMOrcLLJITRef jit, LLVMOrcJITDylibRef dylib, LLVMOrcThreadSafeModuleRef module);

LLVMOrcJITTargetAddress LLJITLookup(LLVMOrcLLJITRef jit, const char *name);

LLVMBool VerifyModule(LLVMModuleRef module);

void AddIncoming(LLVMValueRef phi, LLVMValueRef val, LLVMBasicBlockRef block);

LLVMValueRef BuildICmp(LLVMBuilderRef builder, int op, LLVMValueRef lhs, LLVMValueRef rhs, char *name);

struct JITEnums{
    int64_t codegenlevel;
    int64_t reloc;
    int64_t codemodel;
};

struct CmpEnums{
    int64_t inteq;
    int64_t intne;
    int64_t intugt;
    int64_t intuge;
    int64_t intult;
    int64_t intule;
    int64_t intsgt;
    int64_t intsge;
    int64_t intslt;
    int64_t intsle;
    int64_t realeq;
    int64_t realne;
    int64_t realgt;
    int64_t realge;
    int64_t reallt;
    int64_t realle;
    int64_t realord;
};

LLVMTypeRef getResultElementType(LLVMValueRef gep_instr);

LLVMValueRef removeIncomingValue(LLVMValueRef phi, LLVMBasicBlockRef block);

void removePredecessor(LLVMBasicBlockRef current, LLVMBasicBlockRef pred);

LLVMValueRef getFirstNonPhi(LLVMBasicBlockRef block);

LLVMBasicBlockRef splitBasicBlockAtPhi(LLVMBasicBlockRef block);

LLVMValueRef getTerminator(LLVMBasicBlockRef block);

void dumpModule(LLVMModuleRef mod);

void dumpBasicBlock(LLVMBasicBlockRef block);

LLVMValueRef getIncomingValueForBlock(LLVMValueRef phi, LLVMBasicBlockRef block);
