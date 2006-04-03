#ifndef __DERIVEDTYPES_H__
#define __DERIVEDTYPES_H__

#ifdef __cplusplus
extern "C" {
#endif

int     FunctionType_getNumParams(void* FT);
const void*   FunctionType_getParamType(void* FT, int i);
const void*   FunctionType_getReturnType(void* FT);

#ifdef __cplusplus
};
#endif

#endif
