#ifndef HPY_COMMON_RUNTIME_CALL_H
#define HPY_COMMON_RUNTIME_CALL_H

#include <Python.h>
#include "hpy.h"

_HPy_HIDDEN HPy
ctx_CallTupleDict(HPyContext ctx, HPy callable, HPy args, HPy kw);

#endif /* HPY_COMMON_RUNTIME_CALL_H */
