#ifndef __EXECUIONENGINE_H__
#define __EXECUIONENGINE_H__

#ifdef __cplusplus
extern "C" {
#endif

/*
void*   ExecutionEngine__init__M(void* M);
void*   ExecutionEngine__init__MP(void* MP);
*/
void*   ExecutionEngine__create__(void* MP, int ForceInterpreter);
void*   ExecutionEngine_getModule(void* EE);
void    ExecutionEngine_freeMachineCodeForFunction(void* EE, void* F);

// return union and takes std::vector<GenericValue> actually
long long   ExecutionEngine_runFunction(void* EE, void* F, void* A);

#ifdef __cplusplus
};
#endif

#endif
