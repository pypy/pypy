/**
 * Implementation of HPy_BuildValue.
 *
 * Note: :c:func:`HPy_BuildValue` is a runtime helper functions, i.e., it is not
 * a part of the HPy context, but is available to HPy extensions to incorporate
 * at compile time.
 *
 * ``HPy_BuildValue`` creates a new value based on a format string from the
 * values passed in variadic arguments. Returns ``HPy_NULL`` in case of an error
 * and raises an exception.
 *
 * ``HPy_BuildValue`` does not always build a tuple. It builds a tuple only if
 * its format string contains two or more format units. If the format string is
 * empty, it returns ``None``; if it contains exactly one format unit, it
 * returns whatever object is described by that format unit. To force it to
 * return a tuple of size ``0`` or one, parenthesize the format string.
 *
 * Building complex values with ``HPy_BuildValue`` is more convenient than the
 * equivalent code that uses more granular APIs with proper error handling and
 * cleanup. Moreover, ``HPy_BuildValue`` provides straightforward way to port
 * existing code that uses ``Py_BuildValue``.
 *
 * ``HPy_BuildValue`` always returns a new handle that will be owned by the
 * caller. Even an artificial example ``HPy_BuildValue(ctx, "O", h)`` does not
 * simply forward the value stored in ``h`` but duplicates the handle.
 *
 * Supported Formatting Strings
 * ----------------------------
 *
 * Numbers
 * ~~~~~~~
 *
 * ``i (int) [int]``
 *     Convert a plain C int to a Python integer object.
 *
 * ``l (int) [long int]``
 *     Convert a C long int to a Python integer object.
 *
 * ``I (int) [unsigned int]``
 *     Convert a C unsigned int to a Python integer object.
 *
 * ``k (int) [unsigned long]``
 *     Convert a C unsigned long to a Python integer object.
 *
 * ``L (int) [long long]``
 *     Convert a C long long to a Python integer object.
 *
 * ``K (int) [unsigned long long]``
 *     Convert a C unsigned long long to a Python integer object.
 *
 * ``n (int) [HPy_ssize_t]``
 *     Convert a C HPy_ssize_t to a Python integer object.
 *
 * ``f (float) [float]``
 *     Convert a C float to a Python floating point number.
 *
 * ``d (float) [double]``
 *     Convert a C double to a Python floating point number.
 *
 * Collections
 * ~~~~~~~~~~~
 *
 * ``(items) (tuple) [matching-items]``
 *     Convert a sequence of C values to a Python tuple with the same number of items.
 *
 * ``[items] (list) [matching-items]``
 *     Convert a sequence of C values to a Python list with the same number of items.
 *
 * ``{key:value} (dict) [matching-items]``
 *     Convert a sequence of C values to a Python dict with the same number of items.
 *
 * Misc
 * ~~~~~~~
 *
 * ``O (Python object) [HPy]``
 *      Pass an untouched Python object represented by the handle.
 *
 *      If the object passed in is a HPy_NULL, it is assumed that this was caused because
 *      the call producing the argument found an error and set an exception. Therefore,
 *      HPy_BuildValue will also immediately stop and return HPy_NULL but will not raise
 *      any new exception. If no exception has been raised yet, SystemError is set.
 *
 *      Any HPy handle passed to HPy_BuildValue is always owned by the caller. HPy_BuildValue
 *      never closes the handle nor transfers its ownership. If the handle is used, then
 *      HPy_BuildValue creates a duplicate of the handle.
 *
 * ``S (Python object) [HPy]``
 *      Alias for 'O'.
 *
 * API
 * ---
 *
 */

#include "hpy.h"
#include <stdarg.h>
#include <stdio.h>

#define MESSAGE_BUF_SIZE 128

static HPy_ssize_t count_items(HPyContext *ctx, const char *fmt, char end);
static HPy build_tuple(HPyContext *ctx, const char **fmt, va_list *values, HPy_ssize_t size, char expected_end);
static HPy build_list(HPyContext *ctx, const char **fmt, va_list *values, HPy_ssize_t size);
static HPy build_dict(HPyContext *ctx, const char **fmt, va_list *values);
static HPy build_single(HPyContext *ctx, const char **fmt, va_list *values, int *needs_close);

/**
 * Creates a new value based on a format string from the values passed in
 * variadic arguments.
 *
 * :param ctx:
 *     The execution context.
 * :param fmt:
 *     The format string (ASCII only; must not be ``NULL``). For details, see
 *     :ref:`api-reference/build-value:supported formatting strings`.
 * :param ...:
 *     Variable arguments according to the provided format string.
 *
 * :returns:
 *     A handle to the built Python value or ``HPy_NULL`` in case of errors.
 */
HPyAPI_HELPER
HPy HPy_BuildValue(HPyContext *ctx, const char *fmt, ...)
{
    va_list values;
    HPy result;
    va_start(values, fmt);
    HPy_ssize_t size = count_items(ctx, fmt, '\0');
    if (size < 0) {
        result = HPy_NULL;
    } else if (size == 0) {
        result = HPy_Dup(ctx, ctx->h_None);
    } else if (size == 1) {
        int needs_close;
        result = build_single(ctx, &fmt, &values, &needs_close);
        if (!needs_close) {
            result = HPy_Dup(ctx, result);
        }
    } else {
        result = build_tuple(ctx, &fmt, &values, size, '\0');
    }
    va_end(values);
    return result;
}

static HPy_ssize_t count_items(HPyContext *ctx, const char *fmt, char end)
{
    HPy_ssize_t level = 0, result = 0;
    char top_level_par = 'X';
    while (level != 0 || *fmt != end) {
        char c = *fmt++;
        switch (c) {
            case '\0': {
                // Premature end
                // We try to provide slightly better diagnostics than CPython
                char msg[MESSAGE_BUF_SIZE];
                char par_type;
                if (end == ')') {
                    par_type = '(';
                } else if (end == ']') {
                    par_type = '[';
                } else if (end == '}') {
                    par_type = '{';
                } else {
                    if (level == 0 || top_level_par == 'X') {
                        HPyErr_SetString(ctx, ctx->h_SystemError, "internal error in HPy_BuildValue");
                        return -1;
                    }
                    par_type = top_level_par;
                }
                snprintf(msg, sizeof(msg), "unmatched '%c' in the format string passed to HPy_BuildValue", par_type);
                HPyErr_SetString(ctx, ctx->h_SystemError, msg);
                return -1;
            }

            case '[':
            case '(':
            case '{':
                if (level == 0) {
                    top_level_par = c;
                    result++;
                }
                level++;
                break;

            case ']':
            case ')':
            case '}':
                level--;
                break;

            case ',':
            case ' ':
                break;

            default:
                if (level == 0) {
                    result++;
                }
        }
    }
    return result;
}

static HPy build_single(HPyContext *ctx, const char **fmt, va_list *values, int *needs_close)
{
    char format_char = *(*fmt)++;
    *needs_close = 1;
    switch (format_char) {
        case '(': {
            HPy_ssize_t size = count_items(ctx, *fmt, ')');
            if (size < 0) {
                return HPy_NULL;
            }
            return build_tuple(ctx, fmt, values, size, ')');
        }

        case '[': {
            HPy_ssize_t size = count_items(ctx, *fmt, ']');
            if (size < 0) {
                return HPy_NULL;
            }
            return build_list(ctx, fmt, values, size);
        }

        case '{': {
            return build_dict(ctx, fmt, values);
        }

        case 'i':
            return HPyLong_FromLong(ctx, (long)va_arg(*values, int));

        case 'I':
            return HPyLong_FromUnsignedLong(ctx, (unsigned long)va_arg(*values, unsigned int));

        case 'k':
            return HPyLong_FromUnsignedLong(ctx, va_arg(*values, unsigned long));

        case 'l':
            return HPyLong_FromLong(ctx, va_arg(*values, long));

        case 'L':
            return HPyLong_FromLongLong(ctx, va_arg(*values, long long));

        case 'K':
            return HPyLong_FromUnsignedLongLong(ctx, va_arg(*values, unsigned long long));

        case 'n':
            return HPyLong_FromSsize_t(ctx, va_arg(*values, HPy_ssize_t));

        case 's':
            return HPyUnicode_FromString(ctx, va_arg(*values, const char*));

        case 'O':
        case 'S': {
            HPy handle = va_arg(*values, HPy);
            if (HPy_IsNull(handle)) {
                if (!HPyErr_Occurred(ctx)) {
                    HPyErr_SetString(ctx, ctx->h_SystemError, "HPy_NULL object passed to HPy_BuildValue");
                }
                return handle;
            }
            *needs_close = 0;
            return handle;
        }

        case 'N': {
            HPyErr_SetString(ctx, ctx->h_SystemError,
                             "HPy_BuildValue does not support the 'N' formatting unit. "
                             "Instead, use the 'O' formatting unit and manually close "
                             "the handle in the caller if necessary. HPy API functions "
                             "never 'steal' handles and always make a duplicate handle if "
                             "needed, the 'ownership' of the original handle is never "
                             "'transferred'. ");
            return HPy_NULL;
        }

        case 'f': // Note: floats are promoted to doubles when passed in "..."
        case 'd':
            return HPyFloat_FromDouble(ctx, va_arg(*values, double));

        default: {
            char message[MESSAGE_BUF_SIZE];
            snprintf(message, sizeof(message), "bad format char '%c' in the format string passed to HPy_BuildValue", format_char);
            HPyErr_SetString(ctx, ctx->h_SystemError, message);
            return HPy_NULL;
        }
    } // switch
}

static HPy build_dict(HPyContext *ctx, const char **fmt, va_list *values)
{
    HPy dict = HPyDict_New(ctx);
    int expect_comma = 0;
    while (**fmt != '}' && **fmt != '\0') {
        if (**fmt == ' ') {
            (*fmt)++;
            continue;
        }
        if (**fmt == ',') {
            if (!expect_comma) {
                HPyErr_SetString(ctx, ctx->h_SystemError,
                    "unexpected ',' in the format string passed to HPy_BuildValue");
                HPy_Close(ctx, dict);
                return HPy_NULL;
            }
            (*fmt)++;
            expect_comma = 0;
            continue;
        } else {
            if (expect_comma) {
                HPyErr_SetString(ctx, ctx->h_SystemError,
                    "missing ',' in the format string passed to HPy_BuildValue");
                HPy_Close(ctx, dict);
                return HPy_NULL;
            }
        }
        int needs_key_close, needs_value_close;
        HPy key = build_single(ctx, fmt, values, &needs_key_close);
        if (HPy_IsNull(key)) {
            HPy_Close(ctx, dict);
            return HPy_NULL;
        }
        if (**fmt != ':') {
            HPyErr_SetString(ctx, ctx->h_SystemError,
                            "missing ':' in the format string passed to HPy_BuildValue");
            if (needs_key_close) {
                HPy_Close(ctx, key);
            }
            HPy_Close(ctx, dict);
            return HPy_NULL;
        } else {
            (*fmt)++;
        }
        HPy value = build_single(ctx, fmt, values, &needs_value_close);
        if (HPy_IsNull(value)) {
            if (needs_key_close) {
                HPy_Close(ctx, key);
            }
            HPy_Close(ctx, dict);
            return HPy_NULL;
        }
        int res = HPy_SetItem(ctx, dict, key, value);
        if (needs_key_close) {
            HPy_Close(ctx, key);
        }
        if (needs_value_close) {
            HPy_Close(ctx, value);
        }
        if (res < 0) {
            HPy_Close(ctx, dict);
            return HPy_NULL;
        }

        expect_comma = 1;
    }
    if (**fmt != '}') {
        // count_items does not check the type of the matching paren, that's what we do here
        HPy_Close(ctx, dict);
        HPyErr_SetString(ctx, ctx->h_SystemError,
                         "unmatched '{' in the format string passed to HPy_BuildValue");
        return HPy_NULL;
    }
    ++*fmt;
    return dict;
}

static HPy build_list(HPyContext *ctx, const char **fmt, va_list *values, HPy_ssize_t size)
{
    HPyListBuilder builder = HPyListBuilder_New(ctx, size);
    for (HPy_ssize_t i = 0; i < size; ++i) {
        int needs_close;
        HPy item = build_single(ctx, fmt, values, &needs_close);
        if (HPy_IsNull(item)) {
            HPyListBuilder_Cancel(ctx, builder);
            return HPy_NULL;
        }
        HPyListBuilder_Set(ctx, builder, i, item);
        if (needs_close) {
            HPy_Close(ctx, item);
        }
        if (**fmt == ',') {
            (*fmt)++;
        }
    }
    if (**fmt != ']') {
        // count_items does not check the type of the matching paren, that's what we do here
        HPyListBuilder_Cancel(ctx, builder);
        HPyErr_SetString(ctx, ctx->h_SystemError,
                         "unmatched '[' in the format string passed to HPy_BuildValue");
        return HPy_NULL;
    }
    ++*fmt;
    return HPyListBuilder_Build(ctx, builder);
}

static HPy build_tuple(HPyContext *ctx, const char **fmt, va_list *values, HPy_ssize_t size, char expected_end)
{
    HPyTupleBuilder builder = HPyTupleBuilder_New(ctx, size);
    for (HPy_ssize_t i = 0; i < size; ++i) {
        int needs_close;
        HPy item = build_single(ctx, fmt, values, &needs_close);
        if (HPy_IsNull(item)) {
            HPyTupleBuilder_Cancel(ctx, builder);
            return HPy_NULL;
        }
        HPyTupleBuilder_Set(ctx, builder, i, item);
        if (needs_close) {
            HPy_Close(ctx, item);
        }
        if (**fmt == ',') {
            (*fmt)++;
        }
    }
    if (**fmt != expected_end) {
        // count_items does not check the type of the matching paren, that's what we do here
        // if expected_end == '\0', then there would have to be a bug in count_items
        HPyTupleBuilder_Cancel(ctx, builder);
        if (expected_end == '\0') {
            HPyErr_SetString(ctx, ctx->h_SystemError, "internal error in HPy_BuildValue");
        } else {
            HPyErr_SetString(ctx, ctx->h_SystemError,
                             "unmatched '[' in the format string passed to HPy_BuildValue");
        }
        return HPy_NULL;
    }
    if (expected_end != '\0') {
        ++*fmt;
    }
    return HPyTupleBuilder_Build(ctx, builder);
}
