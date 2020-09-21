#ifndef HPY_COMMON_RUNTIME_LISTBUILDER_H
#define HPY_COMMON_RUNTIME_LISTBUILDER_H

#include <Python.h>
#include "hpy.h"
#include "common/hpytype.h"


_HPy_HIDDEN HPyListBuilder ctx_ListBuilder_New(HPyContext ctx,
                                               HPy_ssize_t initial_size);
_HPy_HIDDEN void ctx_ListBuilder_Set(HPyContext ctx, HPyListBuilder builder,
                                     HPy_ssize_t index, HPy h_item);
_HPy_HIDDEN HPy ctx_ListBuilder_Build(HPyContext ctx, HPyListBuilder builder);
_HPy_HIDDEN void ctx_ListBuilder_Cancel(HPyContext ctx, HPyListBuilder builder);


#endif /* HPY_COMMON_RUNTIME_LISTBUILDER_H */
