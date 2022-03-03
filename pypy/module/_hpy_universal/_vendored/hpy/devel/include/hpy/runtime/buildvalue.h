#ifndef HPY_COMMON_RUNTIME_BUILDVALUE_H
#define HPY_COMMON_RUNTIME_BUILDVALUE_H

#include "hpy.h"

HPyAPI_HELPER HPy
HPy_BuildValue(HPyContext *ctx, const char *fmt, ...);

#endif /* HPY_COMMON_RUNTIME_BUILDVALUE_H */
