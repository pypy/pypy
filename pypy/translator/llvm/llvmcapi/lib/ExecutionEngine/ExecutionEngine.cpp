#include "llvm/ExecutionEngine/ExecutionEngine.h"

using namespace llvm;

/*
void*   ExecutionEngine__init__M(void* M) {
    return new ExecutionEngine((Module*)M);
}

void*   ExecutionEngine__init__MP(void* MP) {
    return new ExecutionEngine((ModuleProvider*)MP);
}
*/

void*   ExecutionEngine__create__(void* MP, int ForceInterpreter) {
    return ExecutionEngine::create((ModuleProvider*)MP, (bool)ForceInterpreter);
}

void*   ExecutionEngine_getModule(void* EE) {
    return &((ExecutionEngine*)EE)->getModule();
}

int     ExecutionEngine_n_functions(void* EE) { //move to Module?
    Module* mod = &((ExecutionEngine*)EE)->getModule();
    int funccount = 0;
    Module::FunctionListType &fns = mod->getFunctionList();
    for (Module::FunctionListType::const_iterator ii = fns.begin(); ii != fns.end(); ++ii) {
        if (!(ii->isIntrinsic() || ii->isExternal())) {
            funccount += 1;
        }
    }
    return funccount;
}

int     Module_function_exists(void* EE, const char* funcname) { //move to Module?
    Module* mod = &((ExecutionEngine*)EE)->getModule();
    Module::FunctionListType &fns = mod->getFunctionList();
    for (Module::FunctionListType::const_iterator ii = fns.begin(); ii != fns.end(); ++ii) {
        if (!(ii->isIntrinsic() || ii->isExternal())) {
            if (ii->getName() == funcname) {
                return 1;
            }
        }
    }
    return 0;
}
