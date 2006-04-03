#ifndef __MODULE_H__
#define __MODULE_H__

#ifdef __cplusplus
extern "C" {
#endif

void*       Module__init__(const char* ModuleID);
const char* Module_getModuleIdentifier(void* M);
void        Module_setModuleIdentifier(void* M, const char* ID);
const char* Module_getTargetTriple(void* M);
void        Module_setTargetTriple(void* M, const char* T);
const char* Module_getModuleInlineAsm(void* M);
void        Module_setModuleInlineAsm(void* M, const char* Asm);
void*       Module_getNamedFunction(void* M, const char* fnname);

// global function that seem to better fit here
void        Module_ParseAssemblyString(void* M, const char* AsmString);
int         Module_verifyModule(void* M);

// helpers
int         Module_n_functions(void* M);
int         Module_function_exists(void* M, const char* fnname);

#ifdef __cplusplus
};
#endif

#endif
