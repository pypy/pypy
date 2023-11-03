#include <string.h>
#include <stdio.h>
#include "debug_internal.h"
#include "autogen_debug_ctx_init.h"
#include "hpy/runtime/ctx_funcs.h"
#if defined(_MSC_VER)
# include <malloc.h>   /* for alloca() */
#endif

static struct _HPyContext_s g_debug_ctx = {
    .name = "HPy Debug Mode ABI",
    ._private = NULL,
    .abi_version = HPY_ABI_VERSION,
};

static HPyDebugCtxInfo *init_ctx_info(HPyContext *dctx, HPyContext *uctx) {
    HPyDebugCtxInfo *ctx_info = (HPyDebugCtxInfo*) malloc(sizeof(HPyDebugCtxInfo));
    if (ctx_info == NULL) {
        HPyErr_NoMemory(uctx);
        return NULL;
    }
    dctx->_private = ctx_info;
    ctx_info->magic_number = HPY_DEBUG_CTX_INFO_MAGIC;
    ctx_info->is_valid = false;
    return ctx_info;
}

static HPyContext *copy_debug_context(HPyContext *dctx) {
    HPyDebugInfo *info = get_info(dctx);
    HPyContext *new_dcxt = (HPyContext *) malloc(sizeof(struct _HPyContext_s));
    memcpy(new_dcxt, dctx, sizeof(struct _HPyContext_s));
    HPyDebugCtxInfo *ctx_info = init_ctx_info(new_dcxt, info->uctx);
    if (ctx_info == NULL) {
        return NULL;
    }
    ctx_info->info = info;
    return new_dcxt;
}

static int init_dctx_cache(HPyContext *dctx, HPyDebugInfo *info) {
    // We prefill the context cache to keep it simple
    for (size_t i = 0; i < HPY_DEBUG_CTX_CACHE_SIZE; ++i) {
        info->dctx_cache[i] = copy_debug_context(dctx);
        if (info->dctx_cache[i] == NULL) {
            return -1;
        }
    }
    info->dctx_cache_current_index = 0;
    return 0;
}

// NOTE: at the moment this function assumes that uctx is always the
// same. If/when we migrate to a system in which we can have multiple
// independent contexts, this function should ensure to create a different
// debug wrapper for each of them.
int hpy_debug_ctx_init(HPyContext *dctx, HPyContext *uctx)
{
    if (dctx->_private != NULL) {
        // already initialized
        assert(get_info(dctx)->uctx == uctx); // sanity check
        return 0;
    }
    // initialize debug_info
    // XXX: currently we never free this malloc and
    // the allocations of the cached debug contexts
    HPyDebugCtxInfo *ctx_info = init_ctx_info(dctx, uctx);
    if (ctx_info == NULL) {
        return -1;
    }
    ctx_info->is_valid = true;
    HPyDebugInfo *info = ctx_info->info = malloc(sizeof(HPyDebugInfo));
    if (info == NULL) {
        HPyErr_NoMemory(uctx);
        return -1;
    }
    info->magic_number = HPY_DEBUG_INFO_MAGIC;
    info->uctx = uctx;
    info->current_generation = 0;
    info->uh_on_invalid_handle = HPy_NULL;
    info->closed_handles_queue_max_size = DEFAULT_CLOSED_HANDLES_QUEUE_MAX_SIZE;
    info->protected_raw_data_max_size = DEFAULT_PROTECTED_RAW_DATA_MAX_SIZE;
    info->handle_alloc_stacktrace_limit = 0;
    info->protected_raw_data_size = 0;
    DHQueue_init(&info->open_handles);
    DHQueue_init(&info->closed_handles);
    DHQueue_init(&info->closed_builder);
    debug_ctx_init_fields(dctx, uctx);
    if (init_dctx_cache(dctx, info) != 0) {
        return -1;
    }
    return 0;
}

HPyContext * hpy_debug_get_ctx(HPyContext *uctx)
{
    HPyContext *dctx = &g_debug_ctx;
    if (uctx == dctx) {
        HPy_FatalError(uctx, "hpy_debug_get_ctx: expected an universal ctx, "
                             "got a debug ctx");
    }
    if (hpy_debug_ctx_init(dctx, uctx) < 0) {
        HPyErr_SetString(uctx, uctx->h_SystemError, "Could not create debug context");
        return NULL;
    }
    return dctx;
}

void hpy_debug_set_ctx(HPyContext *dctx)
{
    g_debug_ctx = *dctx;
}

HPy hpy_debug_open_handle(HPyContext *dctx, HPy uh)
{
    return DHPy_open(dctx, uh);
}

HPy hpy_debug_unwrap_handle(HPyContext *dctx, HPy dh)
{
    return DHPy_unwrap(dctx, dh);
}

void hpy_debug_close_handle(HPyContext *dctx, HPy dh)
{
    DHPy_close(dctx, dh);
}

// this function is supposed to be called from gdb: it tries to determine
// whether a handle is universal or debug by looking at the last bit
extern struct _HPyContext_s g_universal_ctx;
#ifndef _MSC_VER
__attribute__((unused))
#endif
static void hpy_magic_dump(HPy h)
{
    int universal = h._i & 1;
    if (universal)
        fprintf(stderr, "\nUniversal handle\n");
    else
        fprintf(stderr, "\nDebug handle\n");

#ifdef _MSC_VER
    fprintf(stderr, "raw value: %Ix (%Id)\n", h._i, h._i);
#else
    fprintf(stderr, "raw value: %lx (%ld)\n", h._i, h._i);
#endif
    if (universal)
        _HPy_Dump(&g_universal_ctx, h);
    else {
        DebugHandle *dh = as_DebugHandle(h);
#ifdef _MSC_VER
        fprintf(stderr, "dh->uh: %Ix\n", dh->uh._i);
#else
        fprintf(stderr, "dh->uh: %lx\n", dh->uh._i);
#endif
        _HPy_Dump(&g_universal_ctx, dh->uh);
    }
}

HPyContext* hpy_debug_get_next_dctx_from_cache(HPyContext *dctx) {
    HPyDebugInfo *info = get_info(dctx);
    HPyContext *result = info->dctx_cache[info->dctx_cache_current_index];
    info->dctx_cache_current_index =
            (info->dctx_cache_current_index + 1) % HPY_DEBUG_CTX_CACHE_SIZE;
    return result;
}

void report_invalid_debug_context() {
    fputs("Error: Wrong HPy Context!\n", stderr);
    char *stacktrace;
    create_stacktrace(&stacktrace, HPY_DEBUG_DEFAULT_STACKTRACE_LIMIT);
    if (stacktrace != NULL) {
        fputs(stacktrace, stderr);
    }
    fflush(stderr);
    abort();
}

/* ~~~~~~~~~~ manually written wrappers ~~~~~~~~~~ */

void debug_ctx_Close(HPyContext *dctx, DHPy dh)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    UHPy uh = DHPy_unwrap(dctx, dh);
    DHPy_close(dctx, dh);
    // Note: this may run __del__
    get_ctx_info(dctx)->is_valid = false;
    HPy_Close(get_info(dctx)->uctx, uh);
    get_ctx_info(dctx)->is_valid = true;
}

static void *
protect_and_associate_data_ptr(DHPy h, void *ptr, HPy_ssize_t data_size)
{
    DebugHandle *handle = as_DebugHandle(h);
    void *new_ptr;
    if (ptr != NULL)
    {
        new_ptr = raw_data_copy(ptr, data_size, true);
        handle->associated_data = new_ptr;
        handle->associated_data_size = data_size;
        return new_ptr;
    }
    else
    {
        handle->associated_data = NULL;
        handle->associated_data_size = 0;
    }
    return NULL;
}

const char *debug_ctx_Unicode_AsUTF8AndSize(HPyContext *dctx, DHPy h, HPy_ssize_t *size)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    const char *ptr = HPyUnicode_AsUTF8AndSize(get_info(dctx)->uctx, DHPy_unwrap(dctx, h), size);
    HPy_ssize_t data_size = 0;
    if (ptr != NULL) {
        data_size = size != NULL ? *size + 1 : (HPy_ssize_t) strlen(ptr) + 1;
    }
    return (const char *)protect_and_associate_data_ptr(h, (void *)ptr, data_size);
}

const char *debug_ctx_Bytes_AsString(HPyContext *dctx, DHPy h)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    HPyContext *uctx = get_info(dctx)->uctx;
    UHPy uh = DHPy_unwrap(dctx, h);
    const char *ptr = HPyBytes_AsString(uctx, uh);
    HPy_ssize_t data_size = 0;
    if (ptr != NULL) {
        // '+ 1' accountd for the implicit null byte termination
        data_size = HPyBytes_Size(uctx, uh) + 1;
    }
    return (const char *)protect_and_associate_data_ptr(h, (void *)ptr, data_size);
}

const char *debug_ctx_Bytes_AS_STRING(HPyContext *dctx, DHPy h)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    HPyContext *uctx = get_info(dctx)->uctx;
    UHPy uh = DHPy_unwrap(dctx, h);
    const char *ptr = HPyBytes_AS_STRING(uctx, uh);
    HPy_ssize_t data_size = 0;
    if (ptr != NULL) {
        // '+ 1' accountd for the implicit null byte termination
        data_size = HPyBytes_GET_SIZE(uctx, uh) + 1;
    }
    return (const char *)protect_and_associate_data_ptr(h, (void *)ptr, data_size);
}

DHPy debug_ctx_Tuple_FromArray(HPyContext *dctx, DHPy dh_items[], HPy_ssize_t n)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    UHPy *uh_items = (UHPy *)alloca(n * sizeof(UHPy));
    for(int i=0; i<n; i++) {
        uh_items[i] = DHPy_unwrap(dctx, dh_items[i]);
    }
    return DHPy_open(dctx, HPyTuple_FromArray(get_info(dctx)->uctx, uh_items, n));
}

DHPy debug_ctx_Type_GenericNew(HPyContext *dctx, DHPy dh_type, const DHPy *dh_args,
                               HPy_ssize_t nargs, DHPy dh_kw)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    UHPy uh_type = DHPy_unwrap(dctx, dh_type);
    UHPy uh_kw = DHPy_unwrap(dctx, dh_kw);
    UHPy *uh_args = (UHPy *)alloca(nargs * sizeof(UHPy));
    for(int i=0; i<nargs; i++) {
        uh_args[i] = DHPy_unwrap(dctx, dh_args[i]);
    }
    get_ctx_info(dctx)->is_valid = false;
    HPy uh_result = HPyType_GenericNew(get_info(dctx)->uctx, uh_type, uh_args,
                                       nargs, uh_kw);
    DHPy dh_result = DHPy_open(dctx, uh_result);
    get_ctx_info(dctx)->is_valid = true;
    return dh_result;
}

DHPy debug_ctx_Type_FromSpec(HPyContext *dctx, HPyType_Spec *spec, HPyType_SpecParam *dparams)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    // dparams might contain some hidden DHPy: we need to manually unwrap them.
    if (dparams != NULL) {
        // count the params
        HPy_ssize_t n = 1;
        for (HPyType_SpecParam *p = dparams; p->kind != 0; p++) {
            n++;
        }
        HPyType_SpecParam *uparams = (HPyType_SpecParam *)alloca(n * sizeof(HPyType_SpecParam));
        for (HPy_ssize_t i=0; i<n; i++) {
            uparams[i].kind = dparams[i].kind;
            uparams[i].object = DHPy_unwrap(dctx, dparams[i].object);
        }
        return DHPy_open(dctx, HPyType_FromSpec(get_info(dctx)->uctx, spec, uparams));
    }
    return DHPy_open(dctx, HPyType_FromSpec(get_info(dctx)->uctx, spec, NULL));
}

static const char *get_builtin_shape_name(HPyType_BuiltinShape shape)
{
#define SHAPE_NAME(SHAPE) \
    case SHAPE:           \
        return #SHAPE;    \

    /* Note: we use a switch here because then the compiler will warn us about
       missing cases if shapes are added to enum 'HPyType_BuiltinShape' */
    switch (shape)
    {
    SHAPE_NAME(HPyType_BuiltinShape_Legacy)
    SHAPE_NAME(HPyType_BuiltinShape_Object)
    SHAPE_NAME(HPyType_BuiltinShape_Type)
    SHAPE_NAME(HPyType_BuiltinShape_Long)
    SHAPE_NAME(HPyType_BuiltinShape_Float)
    SHAPE_NAME(HPyType_BuiltinShape_Unicode)
    SHAPE_NAME(HPyType_BuiltinShape_Tuple)
    SHAPE_NAME(HPyType_BuiltinShape_List)
    }
    return "<unknown shape>";
#undef SHAPE_NAME
}

#define MAKE_debug_ctx_AsStruct(SHAPE) \
    void *debug_ctx_AsStruct_##SHAPE(HPyContext *dctx, DHPy dh) \
    { \
        if (!get_ctx_info(dctx)->is_valid) { \
            report_invalid_debug_context(); \
        } \
        HPyContext *uctx = get_info(dctx)->uctx; \
        UHPy uh = DHPy_unwrap(dctx, dh); \
        UHPy uh_type = HPy_Type(uctx, uh); \
        HPyType_BuiltinShape actual_shape = _HPyType_GetBuiltinShape(uctx, uh_type); \
        HPy_Close(uctx, uh_type); \
        if (actual_shape != HPyType_BuiltinShape_##SHAPE) { \
            const char *actual_shape_name = get_builtin_shape_name(actual_shape); \
            static const char *fmt = "Invalid usage of _HPy_AsStruct_%s" \
                ". Expected shape HPyType_BuiltinShape_%s but got %s"; \
            size_t nbuf = strlen(fmt) + 2 * strlen(#SHAPE) + strlen(actual_shape_name) + 1; \
            char *buf = (char *)alloca(nbuf); \
            snprintf(buf, nbuf, fmt, #SHAPE, #SHAPE, actual_shape_name); \
            HPy_FatalError(uctx, buf); \
        } \
        return _HPy_AsStruct_##SHAPE(uctx, uh); \
    }

MAKE_debug_ctx_AsStruct(Legacy)

MAKE_debug_ctx_AsStruct(Object)

MAKE_debug_ctx_AsStruct(Type)

MAKE_debug_ctx_AsStruct(Long)

MAKE_debug_ctx_AsStruct(Float)

MAKE_debug_ctx_AsStruct(Unicode)

MAKE_debug_ctx_AsStruct(Tuple)

MAKE_debug_ctx_AsStruct(List)

/* ~~~ debug mode implementation of HPyTracker ~~~

   This is a bit special and it's worth explaining what is going on.

   The HPyTracker functions need their own debug mode implementation because
   the debug mode needs to be aware of when a DHPy is closed, for the same
   reason for why we need debug_ctx_Close.

   So, in theory here we should have our own implementation of a
   DebugHPyTracker which manages a growable list of handles, and which calls
   debug_ctx_Close at the end. But, we ALREADY have the logic available, it's
   implemented in ctx_tracker.c.

   So, here we simply implement debug_ctx_Tracker_* in terms of ctx_Tracker_*:
   but note that it's VERY different than what the autogen wrappers do:

     - the autogen wrappers DHPy_unwrap() all the handles before calling the
       "super" implementation. Here we don't, we pass the DHPys directly.

     - the autogen wrappers pass the uctx to the "super" implementation, here
       we pass the dctx.

   Conceptually, it is equivalent to just have our own implementation of a
   growable array, but by using this trick we can easily reuse the existing
   code.

   It is better understood if you think of what happens on PyPy (or any other
   universal implementation): normally, on PyPy HPyTracker_Add calls PyPy's
   own implementation (see interp_tracker.py). But when in debug mode,
   HPyTracker_Add will call the ctx_Tracker_Add defined in ctx_tracker.c,
   completely bypassing PyPy's own tracker (which is fine). Incidentally, this
   also means that if PyPy wants to bundle the debug mode, it also needs to
   compile ctx_tracker.c
*/

HPyTracker debug_ctx_Tracker_New(HPyContext *dctx, HPy_ssize_t size)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    return ctx_Tracker_New(dctx, size);
}

int debug_ctx_Tracker_Add(HPyContext *dctx, HPyTracker ht, DHPy dh)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    return ctx_Tracker_Add(dctx, ht, dh);
}

void debug_ctx_Tracker_ForgetAll(HPyContext *dctx, HPyTracker ht)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    ctx_Tracker_ForgetAll(dctx, ht);
}

void debug_ctx_Tracker_Close(HPyContext *dctx, HPyTracker ht)
{
    if (!get_ctx_info(dctx)->is_valid) {
        report_invalid_debug_context();
    }
    // note: ctx_Tracker_Close internally calls HPy_Close() to close each
    // handle: since we are calling it with the dctx, it will end up calling
    // debug_ctx_Close, which is exactly what we need to properly record that
    // the handles were closed.
    ctx_Tracker_Close(dctx, ht);
}

HPyListBuilder debug_ctx_ListBuilder_New(HPyContext *dctx, HPy_ssize_t size)
{
    return DHPyListBuilder_open(dctx, HPyListBuilder_New(get_info(dctx)->uctx, size));
}

void debug_ctx_ListBuilder_Set(HPyContext *dctx, HPyListBuilder builder, HPy_ssize_t index, DHPy h_item)
{
    HPyListBuilder_Set(get_info(dctx)->uctx, DHPyListBuilder_unwrap(dctx, builder), index, DHPy_unwrap(dctx, h_item));
}

DHPy debug_ctx_ListBuilder_Build(HPyContext *dctx, HPyListBuilder dh_builder)
{
    DebugBuilderHandle *handle = DHPyListBuilder_as_DebugBuilderHandle(dh_builder);
    if (handle == NULL)
        return HPy_NULL;
    HPyContext *uctx = get_info(dctx)->uctx;
    UHPy uh_result = HPyListBuilder_Build(uctx, DHPyListBuilder_unwrap(dctx, dh_builder));
    DHPy_builder_handle_close(dctx, handle);
    return DHPy_open(dctx, uh_result);
}

void debug_ctx_ListBuilder_Cancel(HPyContext *dctx, HPyListBuilder dh_builder)
{
    DebugBuilderHandle *handle = DHPyListBuilder_as_DebugBuilderHandle(dh_builder);
    if (handle == NULL)
        return;
    HPyContext *uctx = get_info(dctx)->uctx;
    HPyListBuilder_Cancel(uctx, DHPyListBuilder_unwrap(dctx, dh_builder));
    DHPy_builder_handle_close(dctx, handle);
}

HPyTupleBuilder debug_ctx_TupleBuilder_New(HPyContext *dctx, HPy_ssize_t size)
{
    return DHPyTupleBuilder_open(dctx, HPyTupleBuilder_New(get_info(dctx)->uctx, size));
}

void debug_ctx_TupleBuilder_Set(HPyContext *dctx, HPyTupleBuilder builder, HPy_ssize_t index, DHPy h_item)
{
    HPyTupleBuilder_Set(get_info(dctx)->uctx, DHPyTupleBuilder_unwrap(dctx, builder), index, DHPy_unwrap(dctx, h_item));
}

DHPy debug_ctx_TupleBuilder_Build(HPyContext *dctx, HPyTupleBuilder dh_builder)
{
    DebugBuilderHandle *handle = DHPyTupleBuilder_as_DebugBuilderHandle(dh_builder);
    if (handle == NULL)
        return HPy_NULL;
    HPyContext *uctx = get_info(dctx)->uctx;
    UHPy uh_result = HPyTupleBuilder_Build(uctx, DHPyTupleBuilder_unwrap(dctx, dh_builder));
    DHPy_builder_handle_close(dctx, handle);
    return DHPy_open(dctx, uh_result);
}

void debug_ctx_TupleBuilder_Cancel(HPyContext *dctx, HPyTupleBuilder dh_builder)
{
    DebugBuilderHandle *handle = DHPyTupleBuilder_as_DebugBuilderHandle(dh_builder);
    if (handle == NULL)
        return;
    HPyContext *uctx = get_info(dctx)->uctx;
    HPyTupleBuilder_Cancel(uctx, DHPyTupleBuilder_unwrap(dctx, dh_builder));
    DHPy_builder_handle_close(dctx, handle);
}

/*
   However, we don't want to raise an exception if you pass a non-type,
   because the CPython version (PyObject_TypeCheck) always succeed and it
   would be too easy to forget to check the return value. We just raise a
   fatal error instead.
 */
int debug_ctx_TypeCheck(HPyContext *dctx, DHPy obj, DHPy type)
{
    HPyContext *uctx = get_info(dctx)->uctx;
    UHPy uh_obj = DHPy_unwrap(dctx, obj);
    UHPy uh_type = DHPy_unwrap(dctx, type);
    assert(!HPy_IsNull(uh_obj));
    assert(!HPy_IsNull(uh_type));
    if (!HPy_TypeCheck(uctx, uh_type, uctx->h_TypeType)) {
        HPy_FatalError(uctx, "HPy_TypeCheck arg 2 must be a type");
    }
    return HPy_TypeCheck(uctx, uh_obj, uh_type);
}

int32_t debug_ctx_ContextVar_Get(HPyContext *dctx, DHPy context_var, DHPy default_value, DHPy *result)
{
    HPyContext *uctx = get_info(dctx)->uctx;
    UHPy uh_context_var = DHPy_unwrap(dctx, context_var);
    UHPy uh_default_value = DHPy_unwrap(dctx, default_value);
    UHPy uh_result;
    assert(!HPy_IsNull(uh_context_var));
    int32_t ret = HPyContextVar_Get(uctx, uh_context_var, uh_default_value, &uh_result);
    if (ret < 0) {
        *result = HPy_NULL;
        return ret;
    }
    *result = DHPy_open(dctx, uh_result);
    return ret;
}

const char *debug_ctx_Type_GetName(HPyContext *dctx, DHPy type)
{
    HPyDebugCtxInfo *ctx_info;
    HPyContext *uctx;
    UHPy uh_type;
    HPy_ssize_t n_name;

    ctx_info = get_ctx_info(dctx);
    if (!ctx_info->is_valid) {
        report_invalid_debug_context();
    }
    uh_type = DHPy_unwrap(dctx, type);
    uctx = ctx_info->info->uctx;
    if (!HPy_TypeCheck(uctx, uh_type, uctx->h_TypeType)) {
        HPy_FatalError(uctx, "HPyType_GetName arg must be a type");
    }
    ctx_info->is_valid = false;
    const char *name = HPyType_GetName(uctx, uh_type);
    ctx_info->is_valid = true;
    n_name = strlen(name) + 1;
    return (const char *)protect_and_associate_data_ptr(type, (void *)name, n_name);
}

int debug_ctx_Type_IsSubtype(HPyContext *dctx, DHPy sub, DHPy type)
{
    HPyDebugCtxInfo *ctx_info;
    HPyContext *uctx;
    int res;

    ctx_info = get_ctx_info(dctx);
    if (!ctx_info->is_valid) {
        report_invalid_debug_context();
    }

    UHPy uh_sub = DHPy_unwrap(dctx, sub);
    uctx = ctx_info->info->uctx;
    if (!HPy_TypeCheck(uctx, uh_sub, uctx->h_TypeType)) {
        HPy_FatalError(uctx, "HPyType_IsSubtype arg 1 must be a type");
    }
    UHPy uh_type = DHPy_unwrap(dctx, type);
    if (!HPy_TypeCheck(uctx, uh_type, uctx->h_TypeType)) {
        HPy_FatalError(uctx, "HPyType_IsSubtype arg 2 must be a type");
    }

    ctx_info->is_valid = false;
    res = HPyType_IsSubtype(uctx, uh_sub, uh_type);
    ctx_info->is_valid = true;
    return res;
}

DHPy debug_ctx_Unicode_Substring(HPyContext *dctx, DHPy str, HPy_ssize_t start, HPy_ssize_t end)
{
    HPyDebugCtxInfo *ctx_info;
    HPyContext *uctx;

    ctx_info = get_ctx_info(dctx);
    if (!ctx_info->is_valid) {
        report_invalid_debug_context();
    }

    HPy uh_str = DHPy_unwrap(dctx, str);
    uctx = ctx_info->info->uctx;
    if (!HPy_TypeCheck(uctx, uh_str, uctx->h_UnicodeType)) {
        HPy_FatalError(uctx, "HPyUnicode_Substring arg 1 must be a Unicode object");
    }
    ctx_info->is_valid = false;
    HPy universal_result = HPyUnicode_Substring(uctx, uh_str, start, end);
    ctx_info->is_valid = true;
    return DHPy_open(dctx, universal_result);
}

DHPy debug_ctx_Call(HPyContext *dctx, DHPy dh_callable, const DHPy *dh_args, size_t nargs, DHPy dh_kwnames)
{
    HPyDebugCtxInfo *ctx_info;
    HPyContext *uctx;

    ctx_info = get_ctx_info(dctx);
    if (!ctx_info->is_valid) {
        report_invalid_debug_context();
    }

    UHPy uh_callable = DHPy_unwrap(dctx, dh_callable);
    UHPy uh_kwnames = DHPy_unwrap(dctx, dh_kwnames);
    uctx = ctx_info->info->uctx;
    HPy_ssize_t nkw;
    if (!HPy_IsNull(uh_kwnames)) {
        if (!HPyTuple_Check(uctx, uh_kwnames)) {
            HPy_FatalError(uctx, "HPy_Call arg 'kwnames' must be a tuple object or HPy_NULL");
        }
        nkw = HPy_Length(uctx, uh_kwnames);
        if (nkw < 0) {
            return HPy_NULL;
        }
    } else {
        nkw = 0;
    }
    const size_t n_all_args = nargs + nkw;
    UHPy *uh_args = (UHPy *)alloca(n_all_args * sizeof(UHPy));
    for(size_t i=0; i < n_all_args; i++) {
        uh_args[i] = DHPy_unwrap(dctx, dh_args[i]);
    }
    ctx_info->is_valid = false;
    DHPy dh_result = DHPy_open(dctx, HPy_Call(uctx, uh_callable, uh_args, nargs, uh_kwnames));
    ctx_info->is_valid = true;
    return dh_result;
}

DHPy debug_ctx_CallMethod(HPyContext *dctx,  DHPy dh_name, const DHPy *dh_args, size_t nargs, DHPy dh_kwnames)
{
    HPyDebugCtxInfo *ctx_info;
    HPyContext *uctx;

    ctx_info = get_ctx_info(dctx);
    if (!ctx_info->is_valid) {
        report_invalid_debug_context();
    }

    UHPy uh_name = DHPy_unwrap(dctx, dh_name);
    UHPy uh_kwnames = DHPy_unwrap(dctx, dh_kwnames);
    uctx = ctx_info->info->uctx;
    HPy_ssize_t nkw;
    if (!HPy_IsNull(uh_kwnames)) {
        if (!HPyTuple_Check(uctx, uh_kwnames)) {
            HPy_FatalError(uctx, "HPy_CallMethod arg 'kwnames' must be a tuple object or HPy_NULL");
        }
        nkw = HPy_Length(uctx, uh_kwnames);
        if (nkw < 0) {
            return HPy_NULL;
        }
    } else {
        nkw = 0;
    }
    const size_t n_all_args = nargs + nkw;
    UHPy *uh_args = (UHPy *)alloca(n_all_args * sizeof(UHPy));
    for(size_t i=0; i < n_all_args; i++) {
        uh_args[i] = DHPy_unwrap(dctx, dh_args[i]);
    }
    ctx_info->is_valid = false;
    DHPy dh_result = DHPy_open(dctx, HPy_CallMethod(uctx, uh_name, uh_args, nargs, uh_kwnames));
    ctx_info->is_valid = true;
    return dh_result;
}
