#ifndef HPY_COMMON_RUNTIME_TUPLE_H
#define HPY_COMMON_RUNTIME_TUPLE_H

#include <Python.h>
#include "hpy.h"

_HPy_HIDDEN HPy ctx_Tuple_FromArray(HPyContext ctx, HPy items[], HPy_ssize_t n);

#endif /* HPY_COMMON_RUNTIME_TUPLE_H */
