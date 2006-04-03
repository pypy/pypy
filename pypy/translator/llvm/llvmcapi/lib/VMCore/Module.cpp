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

const char* Module_getModuleInlineAsm(void* M) {
    return ((Module*)M)->getModuleInlineAsm().c_str();
}

void        Module_setModuleInlineAsm(void* M, const char* Asm) {
    ((Module*)M)->setModuleInlineAsm(Asm);
}

void*       Module_getNamedFunction(void* M, const char* fnname) {
    return ((Module*)M)->getNamedFunction(fnname);
}

// global functions, but they make more sense here
void        Module_ParseAssemblyString(void* M, const char* AsmString) { //from Assembly/Parser.h
    ParseAssemblyString(AsmString, (Module*)M);
}

int         Module_verifyModule(void* M) { //from Analysis/Verifier.h
    return verifyModule(*(Module*)M, ThrowExceptionAction);
}

// helpers
int         Module_n_functions(void* M) {
    Module* mod = (Module*)M;
    int funccount = 0;
    Module::FunctionListType &fns = mod->getFunctionList();
    for (Module::FunctionListType::const_iterator ii = fns.begin(); ii != fns.end(); ++ii) {
        if (!(ii->isIntrinsic() || ii->isExternal())) {
            funccount += 1;
        }
    }
    return funccount;
}

int         Module_function_exists(void* M, const char* fnname) {
    Module* mod = (Module*)M;
    Module::FunctionListType &fns = mod->getFunctionList();
    for (Module::FunctionListType::const_iterator ii = fns.begin(); ii != fns.end(); ++ii) {
        if (!(ii->isIntrinsic() || ii->isExternal())) {
            if (ii->getName() == fnname) {
                return 1;
            }
        }
    }
    return 0;
}
