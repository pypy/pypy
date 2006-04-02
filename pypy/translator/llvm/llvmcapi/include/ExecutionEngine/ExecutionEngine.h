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
int     ExecutionEngine_n_functions(void* EE);
int     ExecutionEngine_function_exists(void* EE, const char* funcname);

#ifdef __cplusplus
};
#endif

#endif
