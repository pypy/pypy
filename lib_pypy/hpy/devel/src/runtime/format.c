/**
 * HPy string formatting helpers.
 *
 * Note: these functions are runtime helper functions, i.e., they are not
 * part of the HPy context ABI, but are available to HPy extensions to
 * incorporate at compile time.
 *
 * The formatting helper functions are: ``HPyUnicode_FromFormat``,
 * ``HPyUnicode_FromFormatV``, and ``HPyErr_Format``.
 *
 * Supported Formatting Units
 * --------------------------
 *
 * ``%%`` - The literal % character.
 *
 * Compatible with C (s)printf:
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 *
 * ``%c [int]``
 *
 * ``%d [int]``
 *
 * ``%u [unsigned int]``
 *
 * ``%ld [long]``
 *
 * ``%li [long]``
 *
 * ``%lu [unsigned long]``
 *
 * ``%lld [long long]``
 *
 * ``%lli [long long]``
 *
 * ``%llu [unsigned long long]``
 *
 * ``%zd [HPy_ssize_t]``
 *
 * ``%zi [HPy_ssize_t]``
 *
 * ``%zu [size_t]``
 *
 * ``%i [int]``
 *
 * ``%x [int]``
 *
 * ``%s [const char*]``
 *
 * ``%p [const void*]``
 *      Guaranteed to start with the literal '0x' regardless of what the
 *      platform’s printf yields. However, there is no guarantee for
 *      zero-padding after the '0x' prefix. Some systems pad the pointer
 *      to 32 or 64 digits depending on the architecture, some do not
 *      zero pad at all. Moreover, there is no guarantee whether the letters
 *      will be capitalized or not.
 *
 * Python specific:
 * ~~~~~~~~~~~~~~~~
 *
 * ``%A [HPy]``
 *      The result of calling ``HPy_Ascii``.
 *
 * ``%U [HPy]``
 *      A Unicode object.
 *
 * ``%V [HPy, const char*]``
 *      A Unicode object (which may be ``HPy_NULL``) and a null-terminated C character
 *      array as a second parameter (which will be used, if the first parameter
 *      is ``HPy_NULL``).
 *
 * ``%S [HPy]``
 *      The result of calling ``HPy_Str``.
 *
 * ``%R [HPy]``
 *      The result of calling ``HPy_Repr``.
 *
 * Additional flags:
 * ~~~~~~~~~~~~~~~~~
 *
 * The format is ``%[0]{width}.{precision}{formatting-unit}``.
 *
 * The ``precision`` flag for numbers gives the minimal number of digits
 * (i.e., excluding the minus sign). Shorter numbers are padded with zeros.
 * For strings it gives the maximum number of characters, i.e., the string
 * may be shortened if it is longer than ``precision``.
 *
 * The ``width`` determines how many characters should be output. If the
 * formatting result with ``width`` flag applied is shorter, then it is
 * padded from left with spaces. If it is longer, the result will
 * *not* be shortened.
 *
 * The ``0`` flag is supported only for numeric units: if present, the
 * number is padded to desired ``width`` with zeros instead of spaces.
 * Unlike with spaces padding, the minus sign is shifted to the leftmost
 * position with zero padding.
 *
 * The ``width`` formatter unit is number of characters rather than bytes.
 * The precision formatter unit is number of bytes for ``%s`` and ``%V``
 * (if the HPy argument is ``HPy_NULL``), and a number of characters for
 * ``%A``, ``%U``, ``%S``, ``%R`` and ``%V`` (if the HPy argument is not
 * ``HPy_NULL``).
 *
 * Compatibility with CPython API
 * ------------------------------
 *
 * HPy is more strict in these cases:
 *
 * CPython API ignores width, precision, zero-padding flag for formatting
 * units that do not support them: ``%c`` and ``%p``, but HPy raises a system
 * error in such cases.
 *
 * CPython API ignores zero-padding for "string" formatting units, while HPy
 * raises a system error in such cases.
 *
 * Note: users should not rely on these system errors, as HPy may choose
 * to support some of those flags in the future.
 */


/* Implementation notes:
 *
 * The implementation was taken from CPython, but was adapted to be to operate
 * only with utf-8 encoding, because that is how HPy exposes Python strings
 * (i.e., HPyUnicode_AsUTF8AndSize). CPython starts with UCS1 and widens to
 * UCS2,3,4 depending on the largest character encountered so far. We keep
 * everything in utf-8, or in fact in ascii as long as we do not encounter any
 * of the Python specific formatting units such as %S or %V. The only place where
 * we actually need to have special handling for utf-8 variable width encoding
 * is with the width and precision flags for Python specific formatting units.
 *
 * ------------------------------------------------------------------
 * CPython copyrights:
 *
 * Unicode implementation based on original code by Fredrik Lundh,
 * modified by Marc-Andre Lemburg <mal@lemburg.com>.
 *
 * Major speed upgrades to the method implementations at the Reykjavik
 * NeedForSpeed sprint, by Fredrik Lundh and Andrew Dalke.
 *
 * Copyright (c) Corporation for National Research Initiatives.
 *
 * ---------
 * The original string type implementation is:
 * Copyright (c) 1999 by Secret Labs AB
 * Copyright (c) 1999 by Fredrik Lundh
 *
 * ------------------------------------------------------------------
 *
 * Please see the git history of the following files from CPython source
 * code for more authors:
 *
 *  - Objects/unicodeobject.c
 *  - Modules/_testcapi/unicode.c
 */



#include "hpy.h"
#include <string.h>
#include <ctype.h>
#include <stdio.h>

// Maximum code point of Unicode 6.0: 0x10ffff (1,114,111).
#define MAX_UNICODE 0x10ffff

/* maximum number of characters required for output of %lld or %p.
   We need at most ceil(log10(256)*SIZEOF_LONG_LONG) digits,
   plus 1 for the sign.  53/22 is an upper bound for log10(256). */
#define MAX_LONG_LONG_CHARS (2 + (sizeof(long long)*53-1) / 22)

#define MAX(x, y) (((x) > (y)) ? (x) : (y))
#define MIN(x, y) (((x) < (y)) ? (x) : (y))

#define OVERALLOCATE_FACTOR 4

typedef struct {
    char *data_utf8;
    HPy_ssize_t size;
    HPy_ssize_t pos;
    bool memory_error;
} StrWriter;

static void StrWriter_Init(StrWriter *writer, HPy_ssize_t init_size)
{
    memset(writer, 0, sizeof(*writer));
    writer->data_utf8 = (char*) malloc(init_size);
    writer->size = init_size;
}

static bool StrWriter_EnsureSpace(StrWriter *writer, HPy_ssize_t len)
{
    if (len < (writer->size - writer->pos))
        return true;

    HPy_ssize_t add = (writer->size / OVERALLOCATE_FACTOR);
    if (len > add)
        add = len;
    writer->size += add;
    if (writer->size < 0)
        writer->size = HPY_SSIZE_T_MAX;
    char *prev = writer->data_utf8;
    writer->data_utf8 = (char*) realloc(writer->data_utf8, writer->size);
    if (!writer->data_utf8) {
        free(prev);
        writer->memory_error = true;
        return false;
    }
    return true;
}

static void StrWriter_WriteCharRaw(StrWriter *writer, const int c)
{
    assert((writer->size - writer->pos) > 0);
    writer->data_utf8[writer->pos++] = c;
}

static bool StrWriter_WriteChar(StrWriter *writer, const int c)
{
    if (!StrWriter_EnsureSpace(writer, 1))
        return false;
    StrWriter_WriteCharRaw(writer, c);
    return true;
}

static void StrWriter_WriteCharNRaw(StrWriter *writer, char c, HPy_ssize_t n)
{
    assert((writer->size - writer->pos) >= n);
    memset(writer->data_utf8 + writer->pos, c, n);
    writer->pos += n;
}

static void StrWriter_WriteRaw(StrWriter *writer, const char *utf8, HPy_ssize_t len)
{
    assert((writer->size - writer->pos) >= len);
    memcpy(writer->data_utf8 + writer->pos, utf8, len);
    writer->pos += len;
}

static bool StrWriter_Write(StrWriter *writer, const char *utf8, HPy_ssize_t len)
{
    if (!StrWriter_EnsureSpace(writer, len))
        return false;
    StrWriter_WriteRaw(writer, utf8, len);
    return true;
}

static bool StrWriter_WriteWithWidth(StrWriter *writer, const char *utf8, HPy_ssize_t length,
                                     HPy_ssize_t width, HPy_ssize_t precision)
{
    assert(utf8 != NULL);
    if ((precision == -1 || precision >= length)
        && width <= length) {
        return StrWriter_Write(writer, utf8, length);
    }

    if (precision != -1)
        length = MIN(precision, length);

    HPy_ssize_t arglen = MAX(length, width);
    if (!StrWriter_EnsureSpace(writer, arglen))
        return false;

    if (width > length) {
        HPy_ssize_t fill = width - length;
        StrWriter_WriteCharNRaw(writer, ' ', fill);
    }

    assert((writer->size - writer->pos) >= length);
    memcpy(writer->data_utf8 + writer->pos, utf8, length);
    writer->pos += length;
    return true;
}

static bool StrWriter_WriteUnicode(HPyContext *ctx, StrWriter *writer, HPy h,
                                   HPy_ssize_t width, HPy_ssize_t precision)
{
    assert(!HPy_IsNull(h) && HPyUnicode_Check(ctx, h));
    HPy_ssize_t u_size;
    const char *u_str = HPyUnicode_AsUTF8AndSize(ctx, h, &u_size);
    if (!u_str)
        return false;
    // We cannot use strlen(u_str), this may not be ascii only string
    HPy_ssize_t length = HPy_Length(ctx, h);

    if ((precision == -1 || precision >= length)
        && width <= length) {
        return StrWriter_Write(writer, u_str, u_size);
    }

    if (precision != -1)
        length = MIN(precision, length);

    HPy_ssize_t extra = length - u_size;
    HPy_ssize_t arglen = MAX(length, width) + extra;
    if (!StrWriter_EnsureSpace(writer, arglen))
        return false;

    if (width > length) {
        HPy_ssize_t fill = width - length;
        StrWriter_WriteCharNRaw(writer, ' ', fill);
    }

    if (length == u_size || precision == -1) {
        return StrWriter_Write(writer, u_str, u_size);
    } else {
        // we need to take "precision" many characters from the utf-8 string:
        HPy_ssize_t chars_count = 0;
        while (chars_count < precision) {
            assert(chars_count < u_size);
            assert((writer->size - writer->pos) > 0);
            writer->data_utf8[writer->pos++] = *u_str;
            if ((*u_str & 0xc0) != 0x80)
                chars_count++;
            u_str++;
        }
        return true;
    }
}

static bool StrWriter_DupAndWriteUnicode(HPyContext *ctx, StrWriter *writer, HPy h_unicode,
                                         HPy_ssize_t width, HPy_ssize_t precision)
{
    // We are dupping the handle, such that we can release the C string
    // as soon as possible by closing the handle immediately here
    HPy h = HPy_Dup(ctx, h_unicode);
    bool u_result = StrWriter_WriteUnicode(ctx, writer, h, width, precision);
    HPy_Close(ctx, h);
    return u_result;
}

static bool StrWriter_WriteFunResult(HPyContext *ctx, StrWriter *writer, HPy (fun)(HPyContext*, HPy), HPy arg,
                                     HPy_ssize_t width, HPy_ssize_t precision)
{
    if (HPy_IsNull(arg)) {
        HPyErr_SetString(ctx, ctx->h_SystemError,
         "HPy_NULL passed as value for formatting unit '%S' or '%R' or '%A'");
        return false;
    }
    HPy h = fun(ctx, arg);
    if (HPy_IsNull(h))
        return false;
    bool u_result = StrWriter_WriteUnicode(ctx, writer, h, width, precision);
    HPy_Close(ctx, h);
    return u_result;
}

static void StrWriter_Close(StrWriter *writer)
{
    free(writer->data_utf8);
    writer->data_utf8 = NULL;
}

static HPy StrWriter_ToUnicode(HPyContext *ctx, StrWriter *writer)
{
    if (writer->data_utf8 == NULL && !writer->memory_error) {
        return HPy_NULL;
    }
    if (writer->memory_error || !StrWriter_Write(writer, "\0", 1)) {
        HPyErr_SetString(ctx, ctx->h_MemoryError, "cannot allocate memory for string format");
        return HPy_NULL;
    }
    HPy result = HPyUnicode_FromString(ctx, writer->data_utf8);
    StrWriter_Close(writer);
    return result;
}

static const char*
unicode_fromformat_arg(HPyContext *ctx, StrWriter *writer, const char *f, va_list *vargs)
{
    HPy_ssize_t len;
    HPy_ssize_t width;
    HPy_ssize_t precision;
    int longflag;
    int longlongflag;
    int size_tflag;
    HPy_ssize_t fill;

    f++;
    if (*f == '%') {
        if (!StrWriter_WriteChar(writer, '%'))
            return NULL;
        f++;
        return f;
    }

    bool zeropad = false;
    if (*f == '0') {
        zeropad = true;
        f++;
    }

    /* parse the width.precision part, e.g. "%2.5s" => width=2, precision=5 */
    width = -1;
    if (isdigit(*f)) {
        width = *f - '0';
        f++;
        while (isdigit((unsigned)*f)) {
            if (width > (HPy_ssize_t) (HPY_SSIZE_T_MAX - ((int)*f - '0')) / 10) {
                HPyErr_SetString(ctx, ctx->h_ValueError,
                                "width too big");
                return NULL;
            }
            width = (width * 10) + (*f - '0');
            f++;
        }
    }
    precision = -1;
    if (*f == '.') {
        f++;
        if (isdigit((unsigned)*f)) {
            precision = (*f - '0');
            f++;
            while (isdigit((unsigned)*f)) {
                if (precision > (HPy_ssize_t) (HPY_SSIZE_T_MAX - ((int)*f - '0')) / 10) {
                    HPyErr_SetString(ctx, ctx->h_ValueError,
                                    "precision too big");
                    return NULL;
                }
                precision = (precision * 10) + (*f - '0');
                f++;
            }
        }
        if (*f == '%') {
            /* "%.3%s" => f points to "3" */
            f--;
        }
    }
    if (*f == '\0') {
        /* bogus format "%.123" => go backward, f points to "3" */
        f--;
    }

    /* Handle %ld, %lu, %lld and %llu. */
    longflag = 0;
    longlongflag = 0;
    size_tflag = 0;
    if (*f == 'l') {
        if (f[1] == 'd' || f[1] == 'u' || f[1] == 'i') {
            longflag = 1;
            ++f;
        }
        else if (f[1] == 'l' &&
                 (f[2] == 'd' || f[2] == 'u' || f[2] == 'i')) {
            longlongflag = 1;
            f += 2;
        }
    }
    /* handle the size_t flag. */
    else if (*f == 'z' && (f[1] == 'd' || f[1] == 'u' || f[1] == 'i')) {
        size_tflag = 1;
        ++f;
    }

    if (zeropad) {
        switch (*f) {
            case 's':
            case 'U':
            case 'V':
            case 'S':
            case 'R':
            case 'A':
            case 'p':
            case 'c':
                HPyErr_Format(ctx, ctx->h_SystemError, "formatting unit '%%%c' does not support 0-padding", *f);
                return NULL;
        }
    }

    switch (*f) {
        case 'c':
        {
            if (precision != -1 || width != -1) {
                HPyErr_SetString(ctx, ctx->h_SystemError,
                                 "formatting unit '%c' does not support width nor precision");
                return NULL;
            }
            int ordinal = va_arg(*vargs, int);
            if (ordinal < 0 || ordinal > MAX_UNICODE) {
                HPyErr_SetString(ctx, ctx->h_OverflowError,
                                "character argument not in range(0x110000)");
                return NULL;
            }
            if (!StrWriter_WriteChar(writer, ordinal))
                return NULL;
            break;
        }

        case 'i':
        case 'd':
        case 'u':
        case 'x':
        {
            /* used by sprintf */
            char buffer[MAX_LONG_LONG_CHARS];
            // size_t arglen;

            if (*f == 'u') {
                if (longflag) {
                    len = snprintf(buffer, sizeof(buffer), "%lu", va_arg(*vargs, unsigned long));
                }
                else if (longlongflag) {
                    len = snprintf(buffer, sizeof(buffer), "%llu", va_arg(*vargs, unsigned long long));
                }
                else if (size_tflag) {
                    len = snprintf(buffer, sizeof(buffer), "%zu", va_arg(*vargs, size_t));
                }
                else {
                    len = snprintf(buffer, sizeof(buffer), "%u", va_arg(*vargs, unsigned int));
                }
            }
            else if (*f == 'x') {
                len = snprintf(buffer, sizeof(buffer), "%x", va_arg(*vargs, int));
            }
            else {
                if (longflag) {
                    len = snprintf(buffer, sizeof(buffer), "%li", va_arg(*vargs, long));
                }
                else if (longlongflag) {
                    len = snprintf(buffer, sizeof(buffer), "%lli", va_arg(*vargs, long long));
                }
                else if (size_tflag) {
                    len = snprintf(buffer, sizeof(buffer), "%zi", va_arg(*vargs, HPy_ssize_t));
                }
                else {
                    len = snprintf(buffer, sizeof(buffer), "%i", va_arg(*vargs, int));
                }
            }
            assert(len >= 0);
            len = MIN((HPy_ssize_t) sizeof(buffer), len);

            int negative = (buffer[0] == '-');
            len -= negative;

            precision = MAX(precision, len);
            width = MAX(width, precision + negative);

            HPy_ssize_t arglen = MAX(precision, width);
            if (!StrWriter_EnsureSpace(writer, arglen))
                return NULL;

            if (width > precision) {
                if (negative && zeropad) {
                    StrWriter_WriteCharRaw(writer, '-');
                }

                fill = width - precision - negative;
                char fillchar = zeropad ? '0' : ' ';
                StrWriter_WriteCharNRaw(writer, fillchar, fill);

                if (negative && !zeropad) {
                    StrWriter_WriteCharRaw(writer, '-');
                }
            }
            if (precision > len) {
                fill = precision - len;
                StrWriter_WriteCharNRaw(writer, '0', fill);
            }

            StrWriter_WriteRaw(writer, &buffer[negative], len);
            break;
        }

        case 'p':
        {
            if (precision != -1 || width != -1) {
                HPyErr_SetString(ctx, ctx->h_SystemError,
                                 "formatting unit '%p' does not support width nor precision");
                return NULL;
            }

            char number[MAX_LONG_LONG_CHARS];

            len = snprintf(number, sizeof(number), "%p", va_arg(*vargs, void*));
            len = MIN((HPy_ssize_t) sizeof(number), len);
            assert(len >= 0);

            /* %p is ill-defined:  ensure leading 0x. */
            if (number[1] == 'X')
                number[1] = 'x';
            else if (number[1] != 'x') {
                memmove(number + 2, number,
                        strlen(number) + 1);
                number[0] = '0';
                number[1] = 'x';
                len += 2;
            }

            if (!StrWriter_Write(writer, number, len))
                return NULL;
            break;
        }

        case 's':
        {
            /* UTF-8 */
            const char *s = va_arg(*vargs, const char*);
            if (!s) {
                HPyErr_SetString(ctx, ctx->h_SystemError, "null c string passed as value for formatting unit '%s'");
                return NULL;
            }
            if (!StrWriter_WriteWithWidth(writer, s, (HPy_ssize_t) strlen(s), width, precision))
                return NULL;
            break;
        }

        case 'U':
        {
            HPy h = va_arg(*vargs, HPy);
            if (HPy_IsNull(h)) {
                HPyErr_SetString(ctx, ctx->h_SystemError, "HPy_NULL passed as value for formatting unit '%U'");
                return NULL;
            }
            if (!StrWriter_DupAndWriteUnicode(ctx, writer, h, width, precision))
                return NULL;
            break;
        }

        case 'V':
        {
            HPy h = va_arg(*vargs, HPy);
            const char *str = va_arg(*vargs, const char *);
            if (!HPy_IsNull(h)) {
                assert(HPyUnicode_Check(ctx, h));
                if (!StrWriter_DupAndWriteUnicode(ctx, writer, h, width, precision))
                    return NULL;
            } else {
                assert(str != NULL);
                if (!StrWriter_WriteWithWidth(writer, str,  (HPy_ssize_t) strlen(str), width, precision))
                    return NULL;
            }
            break;
        }

        case 'S':
        {
            if (!StrWriter_WriteFunResult(ctx, writer, HPy_Str, va_arg(*vargs, HPy), width, precision))
                return NULL;
            break;
        }

        case 'R':
        {
            if (!StrWriter_WriteFunResult(ctx, writer, HPy_Repr, va_arg(*vargs, HPy), width, precision))
                return NULL;
            break;
        }

        case 'A':
        {
            if (!StrWriter_WriteFunResult(ctx, writer, HPy_ASCII, va_arg(*vargs, HPy), width, precision))
                return NULL;
            break;
        }

        default:
            HPyErr_SetString(ctx, ctx->h_SystemError, "invalid format string");
            return NULL;
    }

    f++;
    return f;
}

HPyAPI_HELPER HPy
HPyUnicode_FromFormatV(HPyContext *ctx, const char *format, va_list vargs)
{
    va_list vargs2;
    const char *f;
    StrWriter writer;

    StrWriter_Init(&writer, (HPy_ssize_t) (strlen(format) + 100));

    // Copy varags to be able to pass a reference to a subfunction.
    va_copy(vargs2, vargs);

    for (f = format; *f; ) {
        if (*f == '%') {
            f = unicode_fromformat_arg(ctx, &writer, f, &vargs2);
            if (f == NULL) {
                StrWriter_Close(&writer);
                goto end;
            }
        }
        else {
            const char *p;
            HPy_ssize_t len;

            p = f;
            do
            {
                if ((unsigned char)*p > 127) {
                    HPyErr_Format(ctx, ctx->h_ValueError,
                                 "expected an ASCII-encoded format "
                                 "string, got a non-ASCII byte: 0x%02x",
                                 (unsigned char)*p);
                    StrWriter_Close(&writer);
                    goto end;
                }
                p++;
            }
            while (*p != '\0' && *p != '%');
            len = p - f;

            if (!StrWriter_Write(&writer, f, len)) {
                StrWriter_Close(&writer);
                goto end;
            }

            f = p;
        }
    }
end:
    va_end(vargs2);
    return StrWriter_ToUnicode(ctx, &writer);
}

HPyAPI_HELPER HPy
HPyUnicode_FromFormat(HPyContext *ctx, const char *fmt, ...)
{
    va_list vargs;
    va_start(vargs, fmt);
    HPy ret = HPyUnicode_FromFormatV(ctx, fmt, vargs);
    va_end(vargs);
    return ret;
}

HPyAPI_HELPER HPy
HPyErr_Format(HPyContext *ctx, HPy h_type, const char *fmt, ...)
{
    va_list vargs;
    va_start(vargs, fmt);
    HPy h_str = HPyUnicode_FromFormatV(ctx, fmt, vargs);
    va_end(vargs);
    HPyErr_SetObject(ctx, h_type, h_str);
    HPy_Close(ctx, h_str);
    return HPy_NULL;
}
