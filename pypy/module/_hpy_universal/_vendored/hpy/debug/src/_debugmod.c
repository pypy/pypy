// Python-level interface for the _debug module. Written in HPy itself, the
// idea is that it should be reusable by other implementations

// NOTE: hpy.debug._debug is loaded using the UNIVERSAL ctx. To make it
// clearer, we will use "uctx" and "dctx" to distinguish them.

#include "hpy.h"
#include "debug_internal.h"

static UHPy new_DebugHandleObj(HPyContext *uctx, UHPy u_DebugHandleType,
                               DebugHandle *handle);

HPY_MOD_EMBEDDABLE(_trace)

HPyDef_METH(new_generation, "new_generation", HPyFunc_NOARGS)
static UHPy new_generation_impl(HPyContext *uctx, UHPy self)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    info->current_generation++;
    return HPyLong_FromLong(uctx, info->current_generation);
}

static UHPy build_list_of_handles(HPyContext *uctx, UHPy u_self, DHQueue *q,
                                  long gen)
{
    UHPy u_DebugHandleType = HPy_NULL;
    UHPy u_result = HPy_NULL;
    UHPy u_item = HPy_NULL;

    u_DebugHandleType = HPy_GetAttr_s(uctx, u_self, "DebugHandle");
    if (HPy_IsNull(u_DebugHandleType))
        goto error;

    u_result = HPyList_New(uctx, 0);
    if (HPy_IsNull(u_result))
        goto error;

    DHQueueNode *node = q->head;
    while(node != NULL) {
        DebugHandle *dh = (DebugHandle *)node;
        if (dh->generation >= gen) {
            UHPy u_item = new_DebugHandleObj(uctx, u_DebugHandleType, dh);
            if (HPy_IsNull(u_item))
                goto error;
            if (HPyList_Append(uctx, u_result, u_item) == -1)
                goto error;
            HPy_Close(uctx, u_item);
        }
        node = node->next;
    }

    HPy_Close(uctx, u_DebugHandleType);
    return u_result;

 error:
    HPy_Close(uctx, u_DebugHandleType);
    HPy_Close(uctx, u_result);
    HPy_Close(uctx, u_item);
    return HPy_NULL;
}


HPyDef_METH(get_open_handles, "get_open_handles", HPyFunc_O, .doc=
            "Return a list containing all the open handles whose generation is >= "
            "of the given arg")
static UHPy get_open_handles_impl(HPyContext *uctx, UHPy u_self, UHPy u_gen)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);

    long gen = HPyLong_AsLong(uctx, u_gen);
    if (HPyErr_Occurred(uctx))
        return HPy_NULL;

    return build_list_of_handles(uctx, u_self, &info->open_handles, gen);
}

HPyDef_METH(get_closed_handles, "get_closed_handles", HPyFunc_VARARGS,
            .doc="Return a list of all the closed handle in the cache")
static UHPy get_closed_handles_impl(HPyContext *uctx, UHPy u_self, const HPy *args, size_t nargs)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    long gen = 0;
    if (nargs > 0) {
        if (nargs != 1) {
            HPyErr_SetString(uctx, uctx->h_TypeError,
                             "get_closed_handles expects no arguments or exactly one argument");
            return HPy_NULL;
        }
        gen = HPyLong_AsLong(uctx, args[0]);
        if (HPyErr_Occurred(uctx))
            return HPy_NULL;
    }
    return build_list_of_handles(uctx, u_self, &info->closed_handles, gen);
}

HPyDef_METH(get_closed_handles_queue_max_size, "get_closed_handles_queue_max_size", HPyFunc_NOARGS,
            .doc="Return the maximum size of the closed handles queue")
static UHPy get_closed_handles_queue_max_size_impl(HPyContext *uctx, UHPy u_self)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    return HPyLong_FromSsize_t(uctx, info->closed_handles_queue_max_size);
}

HPyDef_METH(set_closed_handles_queue_max_size, "set_closed_handles_queue_max_size", HPyFunc_O,
            .doc="Set the maximum size of the closed handles queue")
static UHPy set_closed_handles_queue_max_size_impl(HPyContext *uctx, UHPy u_self, UHPy u_size)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    HPy_ssize_t size = HPyLong_AsSize_t(uctx, u_size);
    if (HPyErr_Occurred(uctx))
        return HPy_NULL;
    info->closed_handles_queue_max_size = size;
    return HPy_Dup(uctx, uctx->h_None);
}

HPyDef_METH(get_protected_raw_data_max_size, "get_protected_raw_data_max_size", HPyFunc_NOARGS,
            .doc="Return the maximum size of the retained raw memory associated with closed handles")
static UHPy get_protected_raw_data_max_size_impl(HPyContext *uctx, UHPy u_self)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    return HPyLong_FromSsize_t(uctx, info->protected_raw_data_max_size);
}

HPyDef_METH(set_protected_raw_data_max_size, "set_protected_raw_data_max_size", HPyFunc_O,
            .doc="Set the maximum size of the retained raw memory associated with closed handles")
static UHPy set_protected_raw_data_max_size_impl(HPyContext *uctx, UHPy u_self, UHPy u_size)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    HPy_ssize_t size = HPyLong_AsSize_t(uctx, u_size);
    if (HPyErr_Occurred(uctx))
        return HPy_NULL;
    info->protected_raw_data_max_size = size;
    return HPy_Dup(uctx, uctx->h_None);
}

HPyDef_METH(set_on_invalid_handle, "set_on_invalid_handle", HPyFunc_O,
            .doc="Set the function to call when we detect the usage of an invalid handle")
static UHPy set_on_invalid_handle_impl(HPyContext *uctx, UHPy u_self, UHPy u_arg)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    if (HPy_Is(uctx, u_arg, uctx->h_None)) {
        info->uh_on_invalid_handle = HPy_NULL;
    } else if (!HPyCallable_Check(uctx, u_arg)) {
        HPyErr_SetString(uctx, uctx->h_TypeError, "Expected a callable object");
        return HPy_NULL;
    } else {
        info->uh_on_invalid_handle = HPy_Dup(uctx, u_arg);
    }
    return HPy_Dup(uctx, uctx->h_None);
}

HPyDef_METH(set_on_invalid_builder_handle, "set_on_invalid_builder_handle", HPyFunc_O,
            .doc="Set the function to call when we detect the usage of an invalid builder handle")
static UHPy set_on_invalid_builder_handle_impl(HPyContext *uctx, UHPy u_self, UHPy u_arg)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    if (HPy_Is(uctx, u_arg, uctx->h_None)) {
        info->uh_on_invalid_builder_handle = HPy_NULL;
    } else if (!HPyCallable_Check(uctx, u_arg)) {
        HPyErr_SetString(uctx, uctx->h_TypeError, "Expected a callable object");
        return HPy_NULL;
    } else {
        info->uh_on_invalid_builder_handle = HPy_Dup(uctx, u_arg);
    }
    return HPy_Dup(uctx, uctx->h_None);
}

HPyDef_METH(set_handle_stack_trace_limit, "set_handle_stack_trace_limit", HPyFunc_O,
            .doc="Set the limit to captured HPy handles allocations stack traces. "
                "None means do not capture the stack traces.")
static UHPy set_handle_stack_trace_limit_impl(HPyContext *uctx, UHPy u_self, UHPy u_arg)
{
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    HPyDebugInfo *info = get_info(dctx);
    if (HPy_Is(uctx, u_arg, uctx->h_None)) {
        info->handle_alloc_stacktrace_limit = 0;
    } else {
        assert(!HPyErr_Occurred(uctx));
        HPy_ssize_t newlimit = HPyLong_AsSsize_t(uctx, u_arg);
        if (newlimit == -1 && HPyErr_Occurred(uctx)) {
            return HPy_NULL;
        }
        info->handle_alloc_stacktrace_limit = newlimit;
    }
    return HPy_Dup(uctx, uctx->h_None);
}


/* ~~~~~~ DebugHandleType and DebugHandleObject ~~~~~~~~

   This is the applevel view of a DebugHandle/DHPy.

   Note that there are two different ways to expose DebugHandle to applevel:

   1. make DebugHandle itself a Python object: this is simple but means that
      you have to pay the PyObject_HEAD overhead (16 bytes) for all of them

   2. make DebugHandle a plain C struct, and expose them through a
      Python-level wrapper.

   We choose to implement solution 2 because we expect to have many
   DebugHandle around, but to expose only few of them to applevel, when you
   call get_open_handles. This way, we save 16 bytes per DebugHandle.

   This means that you can have different DebugHandleObjects wrapping the same
   DebugHandle. To make it easier to compare them, they expose the .id
   attribute, which is the address of the wrapped DebugHandle. Also,
   DebugHandleObjects compare equal if their .id is equal.
*/

typedef struct {
    DebugHandle *handle;
} DebugHandleObject;

HPyType_HELPERS(DebugHandleObject)

HPyDef_GET(DebugHandle_obj, "obj", .doc="The object which the handle points to")
static UHPy DebugHandle_obj_get(HPyContext *uctx, UHPy self, void *closure)
{
    DebugHandleObject *dh = DebugHandleObject_AsStruct(uctx, self);
    return HPy_Dup(uctx, dh->handle->uh);
}

HPyDef_GET(DebugHandle_id, "id",
           .doc="A numeric identifier representing the underlying universal handle")
static UHPy DebugHandle_id_get(HPyContext *uctx, UHPy self, void *closure)
{
    DebugHandleObject *dh = DebugHandleObject_AsStruct(uctx, self);
    return HPyLong_FromSsize_t(uctx, (HPy_ssize_t)dh->handle);
}

HPyDef_GET(DebugHandle_is_closed, "is_closed",
           .doc="Self-explanatory")
static UHPy DebugHandle_is_closed_get(HPyContext *uctx, UHPy self, void *closure)
{
    DebugHandleObject *dh = DebugHandleObject_AsStruct(uctx, self);
    return HPyBool_FromBool(uctx, dh->handle->is_closed);
}

HPyDef_GET(DebugHandle_raw_data_size, "raw_data_size",
.doc="Size of retained raw memory. FOR TESTS ONLY.")
static UHPy DebugHandle_raw_data_size_get(HPyContext *uctx, UHPy self, void *closure)
{
    DebugHandleObject *dh = DebugHandleObject_AsStruct(uctx, self);
    if (dh->handle->associated_data) {
        return HPyLong_FromSsize_t(uctx, dh->handle->associated_data_size);
    } else {
        return HPyLong_FromLong(uctx, -1);
    }
}

HPyDef_SLOT(DebugHandle_cmp, HPy_tp_richcompare)
static UHPy DebugHandle_cmp_impl(HPyContext *uctx, UHPy self, UHPy o, HPy_RichCmpOp op)
{
    UHPy T = HPy_Type(uctx, self);
    if (!HPy_TypeCheck(uctx, o, T))
        return HPy_Dup(uctx, uctx->h_NotImplemented);
    DebugHandleObject *dh_self = DebugHandleObject_AsStruct(uctx, self);
    DebugHandleObject *dh_o = DebugHandleObject_AsStruct(uctx, o);

    switch(op) {
    case HPy_EQ:
        return HPyBool_FromBool(uctx, dh_self->handle == dh_o->handle);
    case HPy_NE:
        return HPyBool_FromBool(uctx, dh_self->handle != dh_o->handle);
    default:
        return HPy_Dup(uctx, uctx->h_NotImplemented);
    }
}

HPyDef_SLOT(DebugHandle_repr, HPy_tp_repr)
static UHPy DebugHandle_repr_impl(HPyContext *uctx, UHPy self)
{
    DebugHandleObject *dh = DebugHandleObject_AsStruct(uctx, self);
    UHPy uh_fmt = HPy_NULL;
    UHPy uh_id = HPy_NULL;
    UHPy uh_args = HPy_NULL;
    UHPy uh_result = HPy_NULL;
    UHPy h_trace_header = HPy_NULL;
    UHPy h_trace = HPy_NULL;

    const char *fmt = NULL;
    if (dh->handle->is_closed)
        fmt = "<DebugHandle 0x%x CLOSED>\n%s%s";
    else
        fmt = "<DebugHandle 0x%x for %r>\n%s%s";

    // XXX: switch to HPyUnicode_FromFormat when we have it
    uh_fmt = HPyUnicode_FromString(uctx, fmt);
    if (HPy_IsNull(uh_fmt))
        goto exit;

    uh_id = HPyLong_FromSsize_t(uctx, (HPy_ssize_t)dh->handle);
    if (HPy_IsNull(uh_id))
        goto exit;

    const char *trace_header;
    const char *trace;
    if (dh->handle->allocation_stacktrace) {
        trace_header = "Allocation stacktrace:\n";
        trace = dh->handle->allocation_stacktrace;
    } else {
        trace_header = "To get the stack trace of where it was allocated use:\nhpy.debug.";
        trace = set_handle_stack_trace_limit.meth.name;
    }
    h_trace_header = HPyUnicode_FromString(uctx, trace_header);
    h_trace = HPyUnicode_FromString(uctx, trace);

    if (dh->handle->is_closed)
        uh_args = HPyTuple_FromArray(uctx, (UHPy[]){uh_id,
                                                    h_trace_header, h_trace}, 3);
    else
        uh_args = HPyTuple_FromArray(uctx, (UHPy[]){uh_id, dh->handle->uh,
                                                    h_trace_header, h_trace}, 4);
    if (HPy_IsNull(uh_args))
        goto exit;

    uh_result = HPy_Remainder(uctx, uh_fmt, uh_args);

 exit:
    HPy_Close(uctx, uh_fmt);
    HPy_Close(uctx, uh_id);
    HPy_Close(uctx, uh_args);
    HPy_Close(uctx, h_trace);
    HPy_Close(uctx, h_trace_header);
    return uh_result;
}


HPyDef_METH(DebugHandle__force_close, "_force_close",
            HPyFunc_NOARGS, .doc="Close the underlying handle. FOR TESTS ONLY.")
static UHPy DebugHandle__force_close_impl(HPyContext *uctx, UHPy self)
{
    DebugHandleObject *dh = DebugHandleObject_AsStruct(uctx, self);
    HPyContext *dctx = hpy_debug_get_ctx(uctx);
    if (dctx == NULL)
        return HPy_NULL;
    HPy_Close(dctx, as_DHPy(dh->handle));
    return HPy_Dup(uctx, uctx->h_None);
}

static HPyDef *DebugHandleType_defs[] = {
    &DebugHandle_obj,
    &DebugHandle_id,
    &DebugHandle_is_closed,
    &DebugHandle_raw_data_size,
    &DebugHandle_cmp,
    &DebugHandle_repr,
    &DebugHandle__force_close,
    NULL
};

static HPyType_Spec DebugHandleType_spec = {
    .name = "hpy.debug._debug.DebugHandle",
    .basicsize = sizeof(DebugHandleObject),
    .flags = HPy_TPFLAGS_DEFAULT,
    .defines = DebugHandleType_defs,
};


static UHPy new_DebugHandleObj(HPyContext *uctx, UHPy u_DebugHandleType,
                               DebugHandle *handle)
{
    DebugHandleObject *dhobj;
    UHPy u_result = HPy_New(uctx, u_DebugHandleType, &dhobj);
    dhobj->handle = handle;
    return u_result;
}


/* ~~~~~~ definition of the module hpy.debug._debug ~~~~~~~ */

HPyDef_SLOT(module_exec, HPy_mod_exec)
static int module_exec_impl(HPyContext *uctx, HPy m)
{
    UHPy h_DebugHandleType = HPyType_FromSpec(uctx, &DebugHandleType_spec, NULL);
    if (HPy_IsNull(h_DebugHandleType))
        return -1;
    HPy_SetAttr_s(uctx, m, "DebugHandle", h_DebugHandleType);
    HPy_Close(uctx, h_DebugHandleType);
    return 0;
}

static HPyDef *module_defines[] = {
    &new_generation,
    &get_open_handles,
    &get_closed_handles,
    &get_closed_handles_queue_max_size,
    &set_closed_handles_queue_max_size,
    &get_protected_raw_data_max_size,
    &set_protected_raw_data_max_size,
    &set_on_invalid_handle,
    &set_on_invalid_builder_handle,
    &set_handle_stack_trace_limit,
    &module_exec,
    NULL
};

static HPyModuleDef moduledef = {
    .doc = "HPy debug mode",
    .size = 0,
    .defines = module_defines
};

HPy_MODINIT(_debug, moduledef)
