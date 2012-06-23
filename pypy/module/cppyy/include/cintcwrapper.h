#ifndef CPPYY_CINTCWRAPPER
#define CPPYY_CINTCWRAPPER

#include "capi.h"

#ifdef __cplusplus
extern "C" {
#endif // ifdef __cplusplus

    void* cppyy_load_dictionary(const char* lib_name);

#ifdef __cplusplus
}
#endif // ifdef __cplusplus

#endif // ifndef CPPYY_CINTCWRAPPER
