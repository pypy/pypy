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

void    ExecutionEngine_freeMachineCodeForFunction(void* EE, void* F) {
    ExecutionEngine*    ee = (ExecutionEngine*)EE;
    Function*           f  = (Function*)F;
    ee->freeMachineCodeForFunction(f);
}

int     ExecutionEngine_runFunction(void* EE, void* F, int args_vector) {
    ExecutionEngine*    ee = (ExecutionEngine*)EE;
    Function*           f  = (Function*)F;
    std::vector<GenericValue>   args;
    return ee->runFunction(f, args).IntVal;
}
