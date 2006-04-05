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

long long   ExecutionEngine_runFunction(void* EE, void* F, void* A) {
    ExecutionEngine*    ee    = (ExecutionEngine*)EE;
    Function*           f     = (Function*)F;
    long long*          pArgs = (long long*)A;

    int n_params = f->getFunctionType()->getNumParams();
    std::vector<GenericValue>   args;
    GenericValue    gv;
    for (int i=0;i < n_params;i++) {
        gv.LongVal = pArgs[i];
        args.push_back(gv);
    }

    return ee->runFunction(f, args).LongVal;
}
