#include "llvm/Module.h"
#include "llvm/Analysis/Verifier.h"

using namespace llvm;

void*       Module__init__(const char* ModuleID) {
    return new Module(ModuleID);
}

const char* Module_getModuleIdentifier(void* M) {
    return ((Module*)M)->getModuleIdentifier().c_str();
}

void        Module_setModuleIdentifier(void* M, const char* ID) {
    return ((Module*)M)->setModuleIdentifier(ID);
}

const char* Module_getTargetTriple(void* M) {
    return ((Module*)M)->getTargetTriple().c_str();
}

void        Module_setTargetTriple(void* M, const char* T) {
    return ((Module*)M)->setTargetTriple(T);
}

/*
const char* Module_getEndianness(void* M) {
    return ((Module*)M)->getEndianness().c_str();
}

void        Module_setEndianness(void* M, Endianness E) {
    return ((Module*)M)->setEndianness(E);
}

const char* Module_getPointerSize(void* M) {
    return ((Module*)M)->getPointerSize().c_str();
}

void        Module_setPointerSize(void* M, PointerSize PS) {
    return ((Module*)M)->setPointerSize(PS);
}
*/

const char* Module_getModuleInlineAsm(void* M) {
    return ((Module*)M)->getModuleInlineAsm().c_str();
}

void        Module_setModuleInlineAsm(void* M, const char* Asm) {
    ((Module*)M)->setModuleInlineAsm(Asm);
}

void        Module_ParseAssemblyString(void* M, const char* AsmString) { //from Assembly/Parser.h
    ParseAssemblyString(AsmString, (Module*)M);
}

int         Module_verifyModule(void* M) { //from Analysis/Verifier.h
    return verifyModule(*(Module*)M, ThrowExceptionAction);
}
