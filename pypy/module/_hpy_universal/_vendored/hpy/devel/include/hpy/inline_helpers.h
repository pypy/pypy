#ifndef HPY_INLINE_HELPERS_H
#define HPY_INLINE_HELPERS_H

#if defined(_MSC_VER)
# include <malloc.h>  /* for alloca() */
#endif

HPyAPI_FUNC HPy HPyErr_SetFromErrno(HPyContext *ctx, HPy h_type)
{
    return HPyErr_SetFromErrnoWithFilenameObjects(ctx, h_type, HPy_NULL, HPy_NULL);
}

HPyAPI_FUNC HPy HPyErr_SetFromErrnoWithFilenameObject(HPyContext *ctx, HPy h_type, HPy filename)
{
    return HPyErr_SetFromErrnoWithFilenameObjects(ctx, h_type, filename, HPy_NULL);
}

HPyAPI_FUNC HPy HPyTuple_Pack(HPyContext *ctx, HPy_ssize_t n, ...) {
    va_list vargs;
    HPy_ssize_t i;

    if (n == 0) {
        return HPyTuple_FromArray(ctx, (HPy*)NULL, n);
    }
    HPy *array = (HPy *)alloca(n * sizeof(HPy));
    va_start(vargs, n);
    if (array == NULL) {
        va_end(vargs);
        return HPy_NULL;
    }
    for (i = 0; i < n; i++) {
        array[i] = va_arg(vargs, HPy);
    }
    va_end(vargs);
    return HPyTuple_FromArray(ctx, array, n);
}

#endif //HPY_INLINE_HELPERS_H
