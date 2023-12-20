#ifndef HPY_COMMON_RUNTIME_ARGPARSE_H
#define HPY_COMMON_RUNTIME_ARGPARSE_H
#ifdef __cplusplus
extern "C" {
#endif

#include "hpy.h"

HPyAPI_HELPER int
HPyArg_Parse(HPyContext *ctx, HPyTracker *ht, const HPy *args,
             size_t nargs, const char *fmt, ...);

HPyAPI_HELPER int
HPyArg_ParseKeywords(HPyContext *ctx, HPyTracker *ht, const HPy *args,
                     size_t nargs, HPy kwnames, const char *fmt,
                     const char *keywords[], ...);

HPyAPI_HELPER int
HPyArg_ParseKeywordsDict(HPyContext *ctx, HPyTracker *ht, const HPy *args,
                         HPy_ssize_t nargs, HPy kw, const char *fmt,
                         const char *keywords[], ...);

#ifdef __cplusplus
}
#endif
#endif /* HPY_COMMON_RUNTIME_ARGPARSE_H */
