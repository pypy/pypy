#include "trace_internal.h"
#include "tctx.h"

// the default symbol visibility is hidden: the easiest way to export
// these two functions is to write a small wrapper.
HPyContext* pypy_hpy_trace_get_ctx(HPyContext *uctx) {
    return hpy_trace_get_ctx(uctx);
}

int pypy_hpy_trace_ctx_init(HPyContext *tctx, HPyContext *uctx) {
    return hpy_trace_ctx_init(tctx, uctx);
}

int pypy_hpy_trace_ctx_free(HPyContext *tctx) {
    return hpy_trace_ctx_free(tctx);
}

int pypy_hpy_trace_get_nfunc(void) {
    return hpy_trace_get_nfunc();
}

const char * pypy_hpy_trace_get_func_name(int idx) {
    return hpy_trace_get_func_name(idx);
}

HPyModuleDef* pypy_HPyInit__trace() {
    return HPyInit__trace();
}
