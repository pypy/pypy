#ifndef __llvm_H__
#define __llvm_H__

#include "llvm/Module.h"
#include "llvm/ModuleProvider.h"
#include "llvm/Function.h"
#include "llvm/DerivedTypes.h"
#include "llvm/Type.h"
#include "llvm/Analysis/Verifier.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "llvm/ExecutionEngine/GenericValue.h"

using namespace llvm;
#define TypeID int

#ifdef __cplusplus
extern "C" {
#endif

// ExecutionEngine
ExecutionEngine* ExecutionEngine_create(ModuleProvider*,long);
Module& ExecutionEngine_getModule(ExecutionEngine*);
void ExecutionEngine_freeMachineCodeForFunction(ExecutionEngine*,Function*);
GenericValue ExecutionEngine_runFunction(ExecutionEngine*,Function*,GenericValue*);

// ModuleProvider

// ExistingModuleProvider
ExistingModuleProvider* ExistingModuleProvider___init__(Module*);

// Function
void Function_eraseFromParent(Function*);
FunctionType* Function_getFunctionType(Function*);

// FunctionType

// GenericValue

// TypeID

// Type
TypeID* Type_getTypeID(Type*);
Type* Type_getContainedType(Type*,long);
char* Type_getDescription(Type*);

// Module
Module* Module___init__(char*);
char* Module_getModuleIdentifier(Module*);
void Module_setModuleIdentifier(Module*,char*);
char* Module_getTargetTriple(Module*);
void Module_setTargetTriple(Module*,char*);
char* Module_getModuleInlineAsm(Module*);
void Module_setModuleInlineAsm(Module*,char*);
Function* Module_getNamedFunction(Module*,char*);
Function* Module_getOrInsertFunction(Module*,char*,FunctionType*);



#ifdef __cplusplus
};
#endif

#endif  // __llvm_H__
