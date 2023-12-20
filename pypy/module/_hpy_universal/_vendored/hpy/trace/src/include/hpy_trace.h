#ifndef HPY_TRACE_H
#define HPY_TRACE_H

#include "hpy.h"

/*
  This is the main public API for the trace mode, and it's meant to be used
  by hpy.universal implementations (including but not limited to the
  CPython's version of hpy.universal which is included in this repo).

  The idea is that for every uctx there is a corresponding unique tctx which
  wraps it.

  If you call hpy_trace_get_ctx twice on the same uctx, you get the same
  result.
*/

HPyContext * hpy_trace_get_ctx(HPyContext *uctx);
int hpy_trace_ctx_init(HPyContext *tctx, HPyContext *uctx);
int hpy_trace_ctx_free(HPyContext *tctx);
int hpy_trace_get_nfunc(void);
const char * hpy_trace_get_func_name(int idx);

// this is the HPy init function created by HPy_MODINIT. In CPython's version
// of hpy.universal the code is embedded inside the extension, so we can call
// this function directly instead of dlopen it. This is similar to what
// CPython does for its own built-in modules. But we must use the same
// signature as HPy_MODINIT

#ifdef ___cplusplus
extern "C"
#endif
HPy_EXPORTED_SYMBOL
HPyModuleDef* HPyInit__trace();

#ifdef ___cplusplus
extern "C"
#endif
HPy_EXPORTED_SYMBOL
void HPyInitGlobalContext__trace(HPyContext *ctx);

#endif /* HPY_TRACE_H */
