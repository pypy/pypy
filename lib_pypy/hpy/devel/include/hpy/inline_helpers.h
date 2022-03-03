#ifndef HPY_INLINE_HELPERS_H
#define HPY_INLINE_HELPERS_H

HPyAPI_FUNC HPy HPyErr_SetFromErrno(HPyContext *ctx, HPy h_type)
{
    return HPyErr_SetFromErrnoWithFilenameObjects(ctx, h_type, HPy_NULL, HPy_NULL);
}

HPyAPI_FUNC HPy HPyErr_SetFromErrnoWithFilenameObject(HPyContext *ctx, HPy h_type, HPy filename)
{
    return HPyErr_SetFromErrnoWithFilenameObjects(ctx, h_type, filename, HPy_NULL);
}

#endif //HPY_INLINE_HELPERS_H
