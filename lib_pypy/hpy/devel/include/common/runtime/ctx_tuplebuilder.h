#ifndef HPY_COMMON_RUNTIME_TUPLEBUILDER_H
#define HPY_COMMON_RUNTIME_TUPLEBUILDER_H

#include <Python.h>
#include "hpy.h"
#include "common/hpytype.h"


_HPy_HIDDEN HPyTupleBuilder ctx_TupleBuilder_New(HPyContext ctx,
                                                 HPy_ssize_t initial_size);
_HPy_HIDDEN void ctx_TupleBuilder_Set(HPyContext ctx, HPyTupleBuilder builder,
                                      HPy_ssize_t index, HPy h_item);
_HPy_HIDDEN HPy ctx_TupleBuilder_Build(HPyContext ctx, HPyTupleBuilder builder);
_HPy_HIDDEN void ctx_TupleBuilder_Cancel(HPyContext ctx,
                                         HPyTupleBuilder builder);


#endif /* HPY_COMMON_RUNTIME_TUPLEBUILDER_H */
