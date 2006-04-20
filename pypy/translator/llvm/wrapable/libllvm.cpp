// llvm.cpp

#include "libllvm.h"

// Helper functions (mostly for casting returnvalues and parameters)
char* as_c_string(std::string str) {
    return (char*)str.c_str();
}

std::string as_std_string(char* p) {
    return std::string(p);
}

std::vector<GenericValue>   as_vector_GenericValue(GenericValue* gv) {
    std::vector<GenericValue>   gvv;
    gvv.push_back(*gv);
    return gvv;
}

// ExecutionEngine
ExecutionEngine* ExecutionEngine_create(ModuleProvider* P0,long P1) {
    return (ExecutionEngine*)ExecutionEngine::create(P0,P1);
}

Module& ExecutionEngine_getModule(ExecutionEngine* P0) {
    return (Module&)P0->getModule();
}

void ExecutionEngine_freeMachineCodeForFunction(ExecutionEngine* P0,Function* P1) {
    return (void)P0->freeMachineCodeForFunction(P1);
}

GenericValue ExecutionEngine_runFunction(ExecutionEngine* P0,Function* P1,GenericValue* P2) {
    return (GenericValue)P0->runFunction(P1,as_vector_GenericValue(P2));
}


// ModuleProvider

// ExistingModuleProvider
ExistingModuleProvider* ExistingModuleProvider___init__(Module* P0) {
    return new ExistingModuleProvider(P0);
}


// Function
void Function_eraseFromParent(Function* P0) {
    return (void)P0->eraseFromParent();
}

FunctionType* Function_getFunctionType(Function* P0) {
    return (FunctionType*)P0->getFunctionType();
}


// FunctionType

// GenericValue

// TypeID

// Type
TypeID* Type_getTypeID(Type* P0) {
    return (TypeID*)P0->getTypeID();
}

Type* Type_getContainedType(Type* P0,long P1) {
    return (Type*)P0->getContainedType(P1);
}

char* Type_getDescription(Type* P0) {
    return (char*)as_c_string(P0->getDescription());
}


// Module
Module* Module___init__(char* P0) {
    return new Module(as_std_string(P0));
}

char* Module_getModuleIdentifier(Module* P0) {
    return (char*)as_c_string(P0->getModuleIdentifier());
}

void Module_setModuleIdentifier(Module* P0,char* P1) {
    return (void)P0->setModuleIdentifier(P1);
}

char* Module_getTargetTriple(Module* P0) {
    return (char*)as_c_string(P0->getTargetTriple());
}

void Module_setTargetTriple(Module* P0,char* P1) {
    return (void)P0->setTargetTriple(P1);
}

char* Module_getModuleInlineAsm(Module* P0) {
    return (char*)as_c_string(P0->getModuleInlineAsm());
}

void Module_setModuleInlineAsm(Module* P0,char* P1) {
    return (void)P0->setModuleInlineAsm(P1);
}

Function* Module_getNamedFunction(Module* P0,char* P1) {
    return (Function*)P0->getNamedFunction(P1);
}

Function* Module_getOrInsertFunction(Module* P0,char* P1,FunctionType* P2) {
    return (Function*)P0->getOrInsertFunction(P1,P2);
}




// end of llvm.cpp
