/**
 * String formatting helpers. These functions are not part of HPy ABI. The implementation will be linked into HPy extensions.
 */
#ifndef HPY_COMMON_RUNTIME_FORMAT_H
#define HPY_COMMON_RUNTIME_FORMAT_H

#include "hpy.h"

HPyAPI_HELPER HPy
HPyUnicode_FromFormat(HPyContext *ctx, const char *fmt, ...);

HPyAPI_HELPER HPy
HPyUnicode_FromFormatV(HPyContext *ctx, const char *format, va_list vargs);

HPyAPI_HELPER HPy
HPyErr_Format(HPyContext *ctx, HPy h_type, const char *fmt, ...);

#endif /* HPY_COMMON_RUNTIME_FORMAT_H */
