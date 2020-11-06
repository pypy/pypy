/**
 * Implementation of HPyArg_Parse and HPyArg_ParseKeywords.
 *
 * HPyArg_Parse parses positional arguments and replaces PyArg_ParseTuple.
 * HPyArg_ParseKeywords parses positional and keyword arguments and
 * replaces PyArg_ParseTupleAndKeywords.
 *
 * HPy intends to only support the simpler format string types (numbers, bools)
 * and handles. More complex types (e.g. buffers) should be retrieved as
 * handles and then processed further as needed.
 *
 * Supported formatting strings:
 *
 * Numbers
 * -------
 *
 * i (int) [int]
 *     Convert a Python integer to a plain C int.
 *
 * l (int) [long int]
 *     Convert a Python integer to a C long int.
 *
 * d (float) [double]
 *     Convert a Python floating point number to a C double.
 *
 * Handles
 * -------
 *
 * O (object) [HPy *]
 *     Returns an existing handle. Not supported by HPyArg_ParseKeywords as
 *     retrieving an item from the keywords dictionary would require creating
 *     a new handled. Use O+ instead for this case.
 *
 * O+ (object) [HPy *]
 *     Returns a new handle. The new handle must be closed if the argument
 *     parsing returns successfully.
 *
 * Options
 * -------
 *
 * |
 *     Indicates that the remaining arguments in the argument list are optional.
 *     The C variables corresponding to optional arguments should be initialized
 *     to their default value — when an optional argument is not specified, the
 *     contents of the corresponding C variable is not modified.
 *
 * $
 *     HPyArg_ParseKeywords() only: Indicates that the remaining arguments in
 *     the argument list are keyword-only. Currently, all keyword-only arguments
 *     must also be optional arguments, so | must always be specified before $
 *     in the format string.
 *
 * :
 *     The list of format units ends here; the string after the colon is used as
 *     the function name in error messages. : and ; are mutually exclusive and
 *     whichever occurs first takes precedence.
 *
 * ;
 *     The list of format units ends here; the string after the semicolon is
 *     used as the error message instead of the default error message. : and ;
 *     are mutually exclusive and whichever occurs first takes precedence.
 *
 */

#include <stdio.h>
#include "hpy.h"

#define _BREAK_IF_OPTIONAL(current_arg) if (HPy_IsNull(current_arg)) break;
#define _ERR_STRING_MAX_LENGTH 512


static const char *
parse_err_fmt(const char *fmt, const char **err_fmt)
{
    const char *fmt1 = fmt;

    for (; *fmt1 != 0; fmt1++) {
        if (*fmt1 == ':' || *fmt1 == ';') {
            *err_fmt = fmt1;
            break;
        }
    }
    return fmt1;
}


static void
set_error(HPyContext ctx, HPy exc, const char *err_fmt, const char *msg) {
    char err_buf[_ERR_STRING_MAX_LENGTH];
    if (err_fmt == NULL) {
        snprintf(err_buf, _ERR_STRING_MAX_LENGTH, "function %.256s", msg);
    }
    else if (*err_fmt == ':') {
        snprintf(err_buf, _ERR_STRING_MAX_LENGTH, "%.200s() %.256s", err_fmt + 1, msg);
    }
    else {
          snprintf(err_buf, _ERR_STRING_MAX_LENGTH, "%s", err_fmt + 1);
    }
    HPyErr_SetString(ctx, exc, err_buf);
}


static int
parse_item(HPyContext ctx, HPy current_arg, const char **fmt, va_list *vl, const char *err_fmt)
{
    switch (*(*fmt)++) {
    case 'i': {
        int *output = va_arg(*vl, int *);
        _BREAK_IF_OPTIONAL(current_arg);
        long value = HPyLong_AsLong(ctx, current_arg);
        if (value == -1 && HPyErr_Occurred(ctx))
            return 0;
        *output = (int)value;
        break;
    }
    case 'l': {
        long *output = va_arg(*vl, long *);
        _BREAK_IF_OPTIONAL(current_arg);
        long value = HPyLong_AsLong(ctx, current_arg);
        if (value == -1 && HPyErr_Occurred(ctx))
            return 0;
        *output = value;
        break;
    }
    case 'd': {
        double* output = va_arg(*vl, double *);
        _BREAK_IF_OPTIONAL(current_arg);
        double value = HPyFloat_AsDouble(ctx, current_arg);
        if (value == -1.0 && HPyErr_Occurred(ctx))
            return 0;
        *output = value;
        break;
    }
    case 'O': {
        if (**fmt == '+') {
            (*fmt)++;
            HPy *output = va_arg(*vl, HPy *);
            _BREAK_IF_OPTIONAL(current_arg);
            *output = HPy_Dup(ctx, current_arg);
            if (HPy_IsNull(*output))
                return 0;
            break;
        }
        else {
            HPy *output = va_arg(*vl, HPy *);
            _BREAK_IF_OPTIONAL(current_arg);
            *output = current_arg;
        }
        break;
    }
    default:
        set_error(ctx, ctx->h_SystemError, err_fmt, "unknown arg format code");
        return 0;
    }
    return 1;
}


HPyAPI_RUNTIME_FUNC(int)
HPyArg_Parse(HPyContext ctx, HPy *args, HPy_ssize_t nargs, const char *fmt, ...)
{
    const char *fmt1 = fmt;
    const char *err_fmt = NULL;
    const char *fmt_end = NULL;

    int optional = 0;
    HPy_ssize_t i = 0;
    HPy current_arg;

    fmt_end = parse_err_fmt(fmt, &err_fmt);

    va_list vl;
    va_start(vl, fmt);

    while (fmt1 != fmt_end) {
        if (*fmt1 == '|') {
            optional = 1;
            fmt1++;
            continue;
        }
        current_arg = HPy_NULL;
        if (i < nargs) {
            current_arg = args[i];
        }
        if (!HPy_IsNull(current_arg) || optional) {
            if (!parse_item(ctx, current_arg, &fmt1, &vl, err_fmt)) {
                va_end(vl);
                return 0;
            }
        }
        else {
            set_error(ctx, ctx->h_TypeError, err_fmt,
                "required positional argument missing");
            va_end(vl);
            return 0;
        }
        i++;
    }
    if (i < nargs) {
        set_error(ctx, ctx->h_TypeError, err_fmt,
            "mismatched args (too many arguments for fmt)");
        va_end(vl);
        return 0;
    }

    va_end(vl);
    return 1;
}


HPyAPI_RUNTIME_FUNC(int)
HPyArg_ParseKeywords(HPyContext ctx, HPy *args, HPy_ssize_t nargs, HPy kw,
                     const char *fmt, const char *keywords[], ...)
{
    const char *fmt1 = fmt;
    const char *err_fmt = NULL;
    const char *fmt_end = NULL;

    int optional = 0;
    int keyword_only = 0;
    HPy_ssize_t i = 0;
    HPy_ssize_t nkw = 0;
    HPy current_arg;

    fmt_end = parse_err_fmt(fmt, &err_fmt);

    // first count positional only arguments
    while (keywords[nkw] != NULL && !*keywords[nkw]) {
        nkw++;
    }
    // then check and count the rest
    while (keywords[nkw] != NULL) {
        if (!*keywords[nkw]) {
            set_error(ctx, ctx->h_SystemError, err_fmt,
                "empty keyword parameter name");
            return 0;
        }
        nkw++;
    }

    va_list vl;
    va_start(vl, keywords);

    while (fmt1 != fmt_end) {
        if (*fmt1 == '|') {
            optional = 1;
            fmt1++;
            continue;
        }
        if (*fmt1 == '$') {
            optional = 1;
            keyword_only = 1;
            fmt1++;
            continue;
        }
        if (*fmt1 == 'O' && *(fmt1 + 1) != '+') {
            set_error(ctx, ctx->h_SystemError, err_fmt,
                "HPyArg_ParseKeywords cannot use the format character 'O'."
                " Use 'O+' instead and close the the returned handle if the call"
                " returns successfully");
            va_end(vl);
            return 0;
        }
        if (i >= nkw) {
            set_error(ctx, ctx->h_TypeError, err_fmt,
                "mismatched args (too few keywords for fmt)");
            va_end(vl);
            return 0;
        }
        current_arg = HPy_NULL;
        if (i < nargs) {
            if (keyword_only) {
                set_error(ctx, ctx->h_TypeError, err_fmt,
                    "keyword only argument passed as positional argument");
                va_end(vl);
                return 0;
            }
            current_arg = args[i];
        }
        else if (!HPy_IsNull(kw) && *keywords[i]) {
            current_arg = HPy_GetItem_s(ctx, kw, keywords[i]);
            // Clear any KeyError that was raised. If an error was raised
            // current_arg will be HPy_NULL and will be handled appropriately
            // below depending on whether the current argument is optional or
            // not
            HPyErr_Clear(ctx);
        }
        if (!HPy_IsNull(current_arg) || optional) {
            if (!parse_item(ctx, current_arg, &fmt1, &vl, err_fmt)) {
                va_end(vl);
                return 0;
            }
        }
        else {
            set_error(ctx, ctx->h_TypeError, err_fmt,
                "no value for required argument");
            va_end(vl);
            return 0;
        }
        i++;
    }
    if (i != nkw) {
        set_error(ctx, ctx->h_TypeError, err_fmt,
            "mismatched args (too many keywords for fmt)");
        va_end(vl);
        return 0;
    }

    va_end(vl);
    return 1;
}
