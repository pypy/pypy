// Python-level interface for the _trace module. Written in HPy itself, the
// idea is that it should be reusable by other implementations

// NOTE: hpy.trace._trace is loaded using the UNIVERSAL ctx. To make it
// clearer, we will use "uctx" and "tctx" to distinguish them.

#include "hpy.h"
#include "trace_internal.h"

#ifndef _WIN32
#include <limits.h>
#define MAX_SEC (LLONG_MAX / FREQ_NSEC)
#endif

HPY_MOD_EMBEDDABLE(_trace)

static inline int is_empty(const char *s)
{
    return s[0] == '\0';
}

#ifdef _WIN32
static inline HPy win_time_to_ns(HPyContext *uctx, const LONGLONG to_ns, _HPyTime_t t)
{
        return HPyLong_FromLongLong(uctx, t.QuadPart * to_ns);
}

#else
static inline HPy posix_time_to_ns(HPyContext *uctx, HPy *s_to_ns, _HPyTime_t t)
{
    /* Fast-path: If we can fit into a signed 64-bit integer, then do the
       computation in C. This is the case if we can do 't.tv_sec * FREQ_SEC'
       (i.e. converting seconds to nanoseconds) and add 'tv.tv_nsec' without
       overflowing. */
    if (t.tv_sec < MAX_SEC) {
        return HPyLong_FromLongLong(uctx, (long long)t.tv_sec * FREQ_NSEC +
                (long long)t.tv_nsec);
    } else {
        /* Slow-path: do the computation with an (unbound) Python long */
        if (HPy_IsNull(*s_to_ns)) {
            *s_to_ns = HPyLong_FromLongLong(uctx, FREQ_NSEC);
        }

        HPy h_tv_sec = HPyLong_FromLongLong(uctx, t.tv_sec);
        HPy h_tv_sec_as_ns = HPy_Multiply(uctx, h_tv_sec, *s_to_ns);
        HPy_Close(uctx, h_tv_sec);

        HPy tv_nsec = HPyLong_FromLong(uctx, t.tv_nsec);
        HPy res = HPy_Add(uctx, h_tv_sec_as_ns, tv_nsec);
        HPy_Close(uctx, h_tv_sec_as_ns);
        HPy_Close(uctx, tv_nsec);

        return res;
    }
}
#endif

HPyDef_METH(get_durations, "get_durations", HPyFunc_NOARGS)
static HPy get_durations_impl(HPyContext *uctx, HPy self)
{
    HPyContext *tctx = hpy_trace_get_ctx(uctx);
    HPyTraceInfo *info = get_info(tctx);
    HPyTracker ht = HPyTracker_New(uctx, hpy_trace_get_nfunc());

#ifdef _WIN32
    const LONGLONG to_ns = FREQ_NSEC / info->counter_freq.QuadPart;
#else
    HPy s_to_ns = HPy_NULL;
#endif
    HPy res = HPyDict_New(uctx);
    const char *func_name;
    for (int i=0; (func_name = hpy_trace_get_func_name(i)); i++)
    {
        /* skip empty names; those indices denote a context handle */
        if (!is_empty(func_name))
        {
#ifdef _WIN32
            HPy value = win_time_to_ns(uctx, to_ns, info->durations[i]);
#else
            HPy value = posix_time_to_ns(uctx, &s_to_ns, info->durations[i]);
#endif
            HPyTracker_Add(uctx, ht, value);
            if (HPy_IsNull(value))
                goto fail;
            if (HPy_SetItem_s(uctx, res, func_name, value) < 0)
                goto fail;
        }
    }
#ifndef _WIN32
    HPy_Close(uctx, s_to_ns);
#endif
    HPyTracker_Close(uctx, ht);
    return res;
fail:
    HPy_Close(uctx, res);
    HPyTracker_Close(uctx, ht);
    return HPy_NULL;
}

HPyDef_METH(get_call_counts, "get_call_counts", HPyFunc_NOARGS)
static HPy get_call_counts_impl(HPyContext *uctx, HPy self)
{
    HPyContext *tctx = hpy_trace_get_ctx(uctx);
    HPyTraceInfo *info = get_info(tctx);
    HPyTracker ht = HPyTracker_New(uctx, hpy_trace_get_nfunc());
    HPy res = HPyDict_New(uctx);
    const char *func_name;
    for (int i=0; (func_name = hpy_trace_get_func_name(i)); i++)
    {
        /* skip empty names; those indices denote a context handle */
        if (!is_empty(func_name))
        {
            HPy value = HPyLong_FromUnsignedLongLong(uctx,
                    (unsigned long long)info->call_counts[i]);
            HPyTracker_Add(uctx, ht, value);
            if (HPy_IsNull(value))
                goto fail;
            if (HPy_SetItem_s(uctx, res, func_name, value) < 0)
                goto fail;
        }
    }
    HPyTracker_Close(uctx, ht);
    return res;
fail:
    HPy_Close(uctx, res);
    HPyTracker_Close(uctx, ht);
    return HPy_NULL;
}

static int check_and_set_func(HPyContext *uctx, HPy arg, HPy *out)
{
    if (HPy_IsNull(arg)) {
        // not provided -> do not change value
        return 0;
    } else if (HPy_Is(uctx, arg, uctx->h_None)) {
        // None -> clear function
        *out = HPy_NULL;
        return 0;
    } else if (!HPyCallable_Check(uctx, arg)) {
        // not null, not None, not callable -> error
        HPyErr_SetString(uctx, uctx->h_TypeError, "Expected a callable object or None");
        return -1;
    }
    // a callable -> set function
    *out = HPy_Dup(uctx, arg);
    return 0;
}

HPyDef_METH(set_trace_functions, "set_trace_functions", HPyFunc_KEYWORDS,
        .doc="Set the functions to call if an HPy API is entered/exited.")
static HPy set_trace_functions_impl(HPyContext *uctx, HPy self, const HPy *args,
        size_t nargs, HPy kwnames)
{
    HPy h_on_enter = HPy_NULL;
    HPy h_on_exit = HPy_NULL;
    HPyContext *dctx = hpy_trace_get_ctx(uctx);
    HPyTraceInfo *info = get_info(dctx);
    HPyTracker ht;

    static const char *kwlist[] = { "on_enter", "on_exit", NULL };
    if (!HPyArg_ParseKeywords(uctx, &ht, args, nargs, kwnames, "|OO", kwlist,
            &h_on_enter, &h_on_exit)) {
        return HPy_NULL;
    }

    int r = check_and_set_func(uctx, h_on_enter, &info->on_enter_func) < 0 ||
            check_and_set_func(uctx, h_on_exit, &info->on_exit_func) < 0;
    HPyTracker_Close(uctx, ht);
    if (r) {
        return HPy_NULL;
    }
    return HPy_Dup(uctx, uctx->h_None);
}

HPyDef_METH(get_frequency, "get_frequency", HPyFunc_NOARGS,
        .doc="Resolution of the used clock in Hertz.")
static HPy get_frequency_impl(HPyContext *uctx, HPy self)
{
    HPyContext *tctx = hpy_trace_get_ctx(uctx);
    HPyTraceInfo *info = get_info(tctx);
#ifdef _WIN32
    long long f = (long long) info->counter_freq.QuadPart;
#else
    long long f = (long long) info->counter_freq.tv_sec +
            (long long)info->counter_freq.tv_nsec * FREQ_NSEC;
#endif
    return HPyLong_FromLongLong(uctx, f);
}


/* ~~~~~~ definition of the module hpy.trace._trace ~~~~~~~ */

static HPyDef *module_defines[] = {
    &get_durations,
    &get_call_counts,
    &set_trace_functions,
    &get_frequency,
    NULL
};

static HPyModuleDef moduledef = {
    .doc = "HPy trace mode",
    .size = 0,
    .defines = module_defines
};

HPy_MODINIT(_trace, moduledef)
