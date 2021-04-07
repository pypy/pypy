#include "debug_internal.h"

DHPy DHPy_wrap(HPyContext dctx, UHPy uh)
{
    UHPy_sanity_check(uh);
    if (HPy_IsNull(uh))
        return HPy_NULL;
    HPyDebugInfo *info = get_info(dctx);
    DebugHandle *handle = malloc(sizeof(DebugHandle));
    if (handle == NULL) {
        return HPyErr_NoMemory(info->uctx);
    }
    handle->uh = uh;
    handle->generation = info->current_generation;
    handle->prev = NULL;
    handle->next = info->open_handles;
    if (info->open_handles)
        info->open_handles->prev = handle;
    info->open_handles = handle;
    return as_DHPy(handle);
}

void DHPy_close(HPyContext dctx, DHPy dh)
{
    DHPy_sanity_check(dh);
    if (HPy_IsNull(dh))
        return;
    HPyDebugInfo *info = get_info(dctx);
    DebugHandle *handle = as_DebugHandle(dh);

    // remove the handle from the open_handles list
    if (handle->prev)
        handle->prev->next = handle->next;
    if (handle->next)
        handle->next->prev = handle->prev;
    if (info->open_handles == handle)
        info->open_handles = handle->next;

    // TODO: eventually, we want to keep a list of closed handles to be able
    // to detect if you are still using them.
    DHPy_free(dh);
}

void DHPy_free(DHPy dh)
{
    DHPy_sanity_check(dh);
    DebugHandle *handle = as_DebugHandle(dh);
    // this is not strictly necessary, but it increases the chances that you
    // get a clear segfault if you use a freed handle
    handle->uh = HPy_NULL;
    free(handle);
}
