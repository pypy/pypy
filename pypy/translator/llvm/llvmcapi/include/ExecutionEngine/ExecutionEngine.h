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
int     ExecutionEngine_runFunction(void* EE, void* F, int args_vector);

#ifdef __cplusplus
};
#endif

#endif
