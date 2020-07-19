#ifndef HPY_COMMON_RUNTIME_CTX_TYPE_H
#define HPY_COMMON_RUNTIME_CTX_TYPE_H

#include <Python.h>
#include "hpy.h"
#include "common/hpytype.h"

_HPy_HIDDEN void* ctx_Cast(HPyContext ctx, HPy h);
_HPy_HIDDEN HPy ctx_Type_FromSpec(HPyContext ctx, HPyType_Spec *hpyspec);
_HPy_HIDDEN HPy ctx_New(HPyContext ctx, HPy h_type, void **data);

_HPy_HIDDEN PyMethodDef *create_method_defs(HPyDef *hpydefs[],
                                            PyMethodDef *legacy_methods);


#endif /* HPY_COMMON_RUNTIME_CTX_TYPE_H */
