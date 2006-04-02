#ifndef __MODULE_H__
#define __MODULE_H__

#ifdef __cplusplus
extern "C" {
#endif

void*   Module__init__(const char* ModuleID);
const char* Module_getModuleIdentifier(void* M);
void        Module_setModuleIdentifier(void* M, const char* ID);
const char* Module_getTargetTriple(void* M);
void        Module_setTargetTriple(void* M, const char* T);
//const char* Module_getEndianness(void* M);
//void        Module_setEndianness(void* M, Endianness E);
//const char* Module_getPointerSize(void* M);
//void        Module_setPointerSize(void* M, PointerSize PS);
const char* Module_getModuleInlineAsm(void* M);
void        Module_setModuleInlineAsm(void* M, const char* Asm);
void        Module_ParseAssemblyString(void* M, const char* AsmString);
int         Module_verifyModule(void* M);

#ifdef __cplusplus
};
#endif

#endif
