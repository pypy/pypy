#ifndef CPPYY_CINTCWRAPPER
#define CPPYY_CINTCWRAPPER

#include "capi.h"

#ifdef __cplusplus
extern "C" {
#endif // ifdef __cplusplus

    /* misc helpers */
    void* cppyy_load_dictionary(const char* lib_name);

    /* pythonization helpers */
    cppyy_object_t cppyy_create_tf1(const char* funcname, unsigned long address,
        double xmin, double xmax, int npar);

    cppyy_object_t cppyy_ttree_Branch(
        void* vtree, const char* branchname, const char* classname,
        void* addobj, int bufsize, int splitlevel);

    long long cppyy_ttree_GetEntry(void* vtree, long long entry);

    cppyy_object_t cppyy_charp2TString(const char* str);
    cppyy_object_t cppyy_TString2TString(cppyy_object_t ptr);

#ifdef __cplusplus
}
#endif // ifdef __cplusplus

#endif // ifndef CPPYY_CINTCWRAPPER
