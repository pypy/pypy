#include "src/precommondefs.h"
#include <hpy.h>

RPY_EXPORTED HPyContext* pypy_hpy_trace_get_ctx(HPyContext *uctx);
RPY_EXPORTED int pypy_hpy_trace_ctx_init(HPyContext *dctx, HPyContext *uctx);
RPY_EXPORTED int pypy_hpy_trace_get_nfunc(void);
RPY_EXPORTED const char * pypy_hpy_trace_get_func_name(int idx);
RPY_EXPORTED HPyModuleDef* pypy_HPyInit__trace(void);
