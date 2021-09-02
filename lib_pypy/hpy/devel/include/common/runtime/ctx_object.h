#ifndef HPY_COMMON_RUNTIME_CTX_OBJECT_H
#define HPY_COMMON_RUNTIME_CTX_OBJECT_H

#include <Python.h>
#include "hpy.h"

_HPy_HIDDEN void ctx_Dump(HPyContext ctx, HPy h);
_HPy_HIDDEN int ctx_TypeCheck(HPyContext ctx, HPy h_obj, HPy h_type);

#endif /* HPY_COMMON_RUNTIME_CTX_OBJECT_H */
