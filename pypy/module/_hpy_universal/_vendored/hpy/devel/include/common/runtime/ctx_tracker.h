#ifndef HPY_COMMON_RUNTIME_CTX_TRACKER_H
#define HPY_COMMON_RUNTIME_CTX_TRACKER_H

#include "hpy.h"

_HPy_HIDDEN HPyTracker
ctx_Tracker_New(HPyContext ctx, HPy_ssize_t size);

_HPy_HIDDEN int
ctx_Tracker_Add(HPyContext ctx, HPyTracker ht, HPy h);

_HPy_HIDDEN void
ctx_Tracker_ForgetAll(HPyContext ctx, HPyTracker ht);

_HPy_HIDDEN void
ctx_Tracker_Close(HPyContext ctx, HPyTracker ht);

#endif /* HPY_COMMON_RUNTIME_CTX_TRACKER_H */
