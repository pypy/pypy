// Python-level interface for the _debug module. Written in HPy itself, the
// idea is that it should be reusable by other implementations

// NOTE: hpy.debug._debug is loaded using the UNIVERSAL ctx. To make it
// clearer, we will use "uctx" and "dctx" to distinguish them.

#include "hpy.h"
#include "debug_internal.h"

static UHPy new_DebugHandleObj(HPyContext uctx, UHPy u_DebugHandleType,
                               DebugHandle *handle);


HPyDef_METH(new_generation, "new_generation", new_generation_impl, HPyFunc_NOARGS)
static UHPy new_generation_impl(HPyContext uctx, UHPy self)
{
    HPyContext dctx = hpy_debug_get_ctx(uctx);
    HPyDebugInfo *info = get_info(dctx);
    info->current_generation++;
    return HPyLong_FromLong(uctx, info->current_generation);
}


HPyDef_METH(get_open_handles, "get_open_handles", get_open_handles_impl, HPyFunc_O, .doc=
            "Return a list containing all the open handles whose generation is >= "
            "of the given arg")
static UHPy get_open_handles_impl(HPyContext uctx, UHPy u_self, UHPy u_gen)
{
    HPyContext dctx = hpy_debug_get_ctx(uctx);
    HPyDebugInfo *info = get_info(dctx);

    UHPy u_DebugHandleType = HPy_GetAttr_s(uctx, u_self, "DebugHandle");
    if (HPy_IsNull(u_DebugHandleType))
        return HPy_NULL;

    long gen = HPyLong_AsLong(uctx, u_gen);
    if (HPyErr_Occurred(uctx))
        return HPy_NULL;

    UHPy u_result = HPyList_New(uctx, 0);
    if (HPy_IsNull(u_result))
        return HPy_NULL;

    DebugHandle *dh = info->open_handles;
    while(dh != NULL) {
        if (dh->generation >= gen) {
            UHPy u_item = new_DebugHandleObj(uctx, u_DebugHandleType, dh);
            if (HPy_IsNull(u_item))
                return HPy_NULL;
            if (HPyList_Append(uctx, u_result, u_item) == -1) {
                HPy_Close(uctx, u_item);
                HPy_Close(uctx, u_result);
                return HPy_NULL;
            }
            HPy_Close(uctx, u_item);
        }
        dh = dh->next;
    }
    return u_result;
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
    HPyObject_HEAD
    DebugHandle *handle;
} DebugHandleObject;

HPyDef_GET(DebugHandle_obj, "obj", DebugHandle_obj_get,
           .doc="The object which the handle points to")
static UHPy DebugHandle_obj_get(HPyContext uctx, UHPy self, void *closure)
{
    DebugHandleObject *dh = HPy_CAST(uctx, DebugHandleObject, self);
    return HPy_Dup(uctx, dh->handle->uh);
}

HPyDef_GET(DebugHandle_id, "id", DebugHandle_id_get,
           .doc="A numeric identifier representing the underlying universal handle")
static UHPy DebugHandle_id_get(HPyContext uctx, UHPy self, void *closure)
{
    DebugHandleObject *dh = HPy_CAST(uctx, DebugHandleObject, self);
    return HPyLong_FromSsize_t(uctx, (HPy_ssize_t)dh->handle);
}

HPyDef_SLOT(DebugHandle_cmp, DebugHandle_cmp_impl, HPy_tp_richcompare)
static UHPy DebugHandle_cmp_impl(HPyContext uctx, UHPy self, UHPy o, HPy_RichCmpOp op)
{
    UHPy T = HPy_Type(uctx, self);
    if (!HPy_TypeCheck(uctx, o, T))
        return HPy_Dup(uctx, uctx->h_NotImplemented);
    DebugHandleObject *dh_self = HPy_CAST(uctx, DebugHandleObject, self);
    DebugHandleObject *dh_o = HPy_CAST(uctx, DebugHandleObject, o);

    switch(op) {
    case HPy_EQ:
        return HPyBool_FromLong(uctx, dh_self->handle == dh_o->handle);
    case HPy_NE:
        return HPyBool_FromLong(uctx, dh_self->handle != dh_o->handle);
    default:
        return HPy_Dup(uctx, uctx->h_NotImplemented);
    }
}

HPyDef_SLOT(DebugHandle_repr, DebugHandle_repr_impl, HPy_tp_repr)
static UHPy DebugHandle_repr_impl(HPyContext uctx, UHPy self)
{
    DebugHandleObject *dh = HPy_CAST(uctx, DebugHandleObject, self);
    UHPy uh_fmt = HPy_NULL;
    UHPy uh_id = HPy_NULL;
    UHPy uh_args = HPy_NULL;
    UHPy uh_result = HPy_NULL;

    // XXX: switch to HPyUnicode_FromFormat when we have it
    uh_fmt = HPyUnicode_FromString(uctx, "<DebugHandle 0x%x for %r>");
    if (HPy_IsNull(uh_fmt))
        goto exit;

    uh_id = HPyLong_FromSsize_t(uctx, (HPy_ssize_t)dh->handle);
    if (HPy_IsNull(uh_id))
        goto exit;

    uh_args = HPyTuple_FromArray(uctx, (UHPy[]){uh_id, dh->handle->uh}, 2);
    if (HPy_IsNull(uh_args))
        goto exit;

    uh_result = HPy_Remainder(uctx, uh_fmt, uh_args);

 exit:
    HPy_Close(uctx, uh_fmt);
    HPy_Close(uctx, uh_id);
    HPy_Close(uctx, uh_args);
    return uh_result;
}



static HPyDef *DebugHandleType_defs[] = {
    &DebugHandle_obj,
    &DebugHandle_id,
    &DebugHandle_cmp,
    &DebugHandle_repr,
    NULL
};

static HPyType_Spec DebugHandleType_spec = {
    .name = "hpy.debug._debug.DebugHandle",
    .basicsize = sizeof(DebugHandleObject),
    .flags = HPy_TPFLAGS_DEFAULT,
    .defines = DebugHandleType_defs,
};


static UHPy new_DebugHandleObj(HPyContext uctx, UHPy u_DebugHandleType,
                               DebugHandle *handle)
{
    DebugHandleObject *dhobj;
    UHPy u_result = HPy_New(uctx, u_DebugHandleType, &dhobj);
    dhobj->handle = handle;
    return u_result;
}


/* ~~~~~~ definition of the module hpy.debug._debug ~~~~~~~ */

static HPyDef *module_defines[] = {
    &new_generation,
    &get_open_handles,
    NULL
};

static HPyModuleDef moduledef = {
    HPyModuleDef_HEAD_INIT,
    .m_name = "hpy.debug._debug",
    .m_doc = "HPy debug mode",
    .m_size = -1,
    .defines = module_defines
};


HPy_MODINIT(_debug)
static UHPy init__debug_impl(HPyContext uctx)
{
    UHPy m = HPyModule_Create(uctx, &moduledef);
    if (HPy_IsNull(m))
        return HPy_NULL;

    UHPy h_DebugHandleType = HPyType_FromSpec(uctx, &DebugHandleType_spec, NULL);
    if (HPy_IsNull(h_DebugHandleType))
        return HPy_NULL;
    HPy_SetAttr_s(uctx, m, "DebugHandle", h_DebugHandleType);
    HPy_Close(uctx, h_DebugHandleType);
    return m;
}
