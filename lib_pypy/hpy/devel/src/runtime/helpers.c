#include "hpy.h"

/**
 * Create a type and add it as an attribute on the given object. The type is
 * created using :c:func:`HPyType_FromSpec`. The object is often a module that the type
 * is being added to.
 *
 * :param ctx:
 *     The execution context.
 * :param obj:
 *     A handle to the object the type is being added to (often a module).
 * :param name:
 *     The name of the attribute on the object to assign the type to.
 * :param hpyspec:
 *     The type spec to use to create the type.
 * :param params:
 *     The type spec parameters to use to create the type.
 *
 * :returns: ``0`` on failure, ``1`` on success.
 *
 * Examples:
 *
 * Using ``HPyHelpers_AddType`` without any :c:struct:`HPyType_SpecParam`
 * parameters:
 *
 * .. code-block:: c
 *
 *     if (!HPyHelpers_AddType(ctx, module, "MyType", hpyspec, NULL))
 *         return HPy_NULL;
 *     ...
 *
 * Using `HPyHelpers_AddType` with `HPyType_SpecParam` parameters:
 *
 * .. code-block:: c
 *
 *     HPyType_SpecParam params[] = {
 *         { HPyType_SpecParam_Base, ctx->h_LongType },
 *         { 0 }
 *     };
 *
 *     if (!HPyHelpers_AddType(ctx, module, "MyType", hpyspec, params))
 *         return HPy_NULL;
 *     ...
 */
HPyAPI_HELPER int
HPyHelpers_AddType(HPyContext *ctx, HPy obj, const char *name,
                  HPyType_Spec *hpyspec, HPyType_SpecParam *params)
{
    HPy h_type = HPyType_FromSpec(ctx, hpyspec, params);
    if (HPy_IsNull(h_type)) {
        return 0;
    }
    if (HPy_SetAttr_s(ctx, obj, name, h_type) != 0) {
        HPy_Close(ctx, h_type);
        return 0;
    }
    HPy_Close(ctx, h_type);
    return 1;
}

/**
 * Convert positional/keyword argument vector to argument tuple and keywords
 * dictionary.
 *
 * This helper function is useful to convert arguments from HPy's calling
 * convention to the legacy CPython *tp_call* calling convention. HPy's calling
 * convention is similar to CPython's fastcall/vectorcall calling convention
 * where positional and keyword arguments are passed as a C array, the number of
 * positional arguments is explicitly given by an argument and the names of the
 * keyword arguments are provided in a tuple.
 *
 * For an example on how to use this function, see section
 * :ref:`call-migration`.
 *
 * :param ctx:
 *     The execution context.
 * :param args:
 *     A pointer to an array of positional and keyword arguments. This argument
 *     must not be ``NULL`` if ``nargs > 0`` or
 *     ``HPy_Length(ctx, kwnames) > 0``.
 * :param nargs:
 *     The number of positional arguments in ``args``.
 * :param kwnames:
 *     A handle to the tuple of keyword argument names (may be ``HPy_NULL``).
 *     The values of the keyword arguments are also passed in ``args`` appended
 *     to the positional arguments. Argument ``nargs`` does not include the
 *     keyword argument count.
 * :param out_pos_args:
 *     A pointer to a variable where to write the created positional arguments
 *     tuple to. If there are no positional arguments (i.e. ``nargs == 0``),
 *     then ``HPy_NULL`` will be written. The pointer will not be used if any
 *     error occurs during conversion.
 * :param out_kwd:
 *     A pointer to a variable where to write the created keyword arguments
 *     dictionary to. If there are not keyword arguments (i.e.
 *     ``HPy_Length(ctx, kwnames) == 0``), then ``HPy_NULL`` will be written.
 *     The pointer will not be used if any error occurs during conversion.
 *
 * :returns: ``0`` on failure, ``1`` on success.
 */
HPyAPI_HELPER int
HPyHelpers_PackArgsAndKeywords(HPyContext *ctx, const HPy *args, size_t nargs,
                               HPy kwnames, HPy *out_pos_args, HPy *out_kwd)
{
    HPy pos_args, kwd, tmp;
    HPy_ssize_t nkw, i;

    if (out_pos_args == NULL) {
        HPyErr_SetString(ctx, ctx->h_SystemError,
                "argument 'out_pos_args' must not be NULL");
        return 0;
    }
    if (out_kwd == NULL) {
        HPyErr_SetString(ctx, ctx->h_SystemError,
                "argument 'out_kwd' must not be NULL");
        return 0;
    }

    nkw = HPy_IsNull(kwnames) ? 0 : HPy_Length(ctx, kwnames);
    if (nkw < 0) {
        return 0;
    } else if (nkw > 0) {
        kwd = HPyDict_New(ctx);
        for (i=0; i < nkw; i++) {
            tmp = HPy_GetItem_i(ctx, kwnames, i);
            if (HPy_IsNull(tmp)) {
                HPy_Close(ctx, kwd);
                return 0;
            }
            if (HPy_SetItem(ctx, kwd, tmp, args[nargs + i]) < 0) {
                HPy_Close(ctx, tmp);
                HPy_Close(ctx, kwd);
                return 0;
            }
            HPy_Close(ctx, tmp);
        }
    } else {
        assert(nkw == 0);
        kwd = HPy_NULL;
    }
    if (nargs > 0) {
        pos_args = HPyTuple_FromArray(ctx, (HPy *)args, nargs);
        if (HPy_IsNull(pos_args)) {
            HPy_Close(ctx, kwd);
            return 0;
        }
    } else {
        pos_args = HPy_NULL;
    }
    // only write to output variables if everything was successful
    *out_pos_args = pos_args;
    *out_kwd = kwd;
    return 1;
}
