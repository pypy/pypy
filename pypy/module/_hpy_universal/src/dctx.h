#include "src/precommondefs.h"
#include <universal/hpy.h>

RPY_EXPORTED HPyContext pypy_hpy_debug_get_ctx(HPyContext uctx);
RPY_EXPORTED int pypy_hpy_debug_ctx_init(HPyContext dctx, HPyContext uctx);
RPY_EXPORTED void pypy_hpy_debug_set_ctx(HPyContext uctx);
RPY_EXPORTED HPy_ssize_t pypy_hpy_debug_wrap_handle(HPyContext dctx, HPy_ssize_t uh);
RPY_EXPORTED HPy_ssize_t pypy_hpy_debug_unwrap_handle(HPy_ssize_t dh);
RPY_EXPORTED HPy_ssize_t pypy_HPyInit__debug(HPyContext uctx);
