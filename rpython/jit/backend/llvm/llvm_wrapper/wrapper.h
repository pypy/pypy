#pragma once

#include <llvm-c/Target.h>
#include <llvm-c/TargetMachine.h>
#include <llvm-c/Orc.h>
#include <llvm-c/Analysis.h>
#include <stddef.h>
#include <stdio.h>

LLVMBool InitializeNativeTarget(void);

LLVMBool InitializeNativeAsmPrinter(void);

LLVMTargetRef GetTargetFromTriple(const char* triple);

LLVMOrcLLJITRef CreateLLJIT(LLVMOrcLLJITBuilderRef builder);

LLVMErrorRef LLJITAddLLVMIRModule(LLVMOrcLLJITRef jit, LLVMOrcJITDylibRef dylib, LLVMOrcThreadSafeModuleRef module);

LLVMOrcJITTargetAddress LLJITLookup(LLVMOrcLLJITRef jit, const char *name);

LLVMBool VerifyModule(LLVMModuleRef module);
