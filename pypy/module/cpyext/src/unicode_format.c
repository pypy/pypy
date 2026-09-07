#include "Python.h"
#include <stddef.h>
#include <stdint.h>

/* PyUnicode_FromFormatV: a port of CPython 3.12's implementation.  Instead
   of a _PyUnicodeWriter, the output is accumulated as UTF-8 bytes, which is
   PyPy's native representation, and decoded once at the end. */

typedef struct {
    char *buf;
    Py_ssize_t pos;
    Py_ssize_t size;
} fmt_writer;

static int
writer_prepare(fmt_writer *w, Py_ssize_t n)
{
    Py_ssize_t newsize;
    char *newbuf;

    if (n <= w->size - w->pos)
        return 0;
    if (w->pos > PY_SSIZE_T_MAX / 2 - n) {
        PyErr_NoMemory();
        return -1;
    }
    newsize = (w->pos + n) * 2;
    newbuf = PyMem_Realloc(w->buf, newsize);
    if (newbuf == NULL) {
        PyErr_NoMemory();
        return -1;
    }
    w->buf = newbuf;
    w->size = newsize;
    return 0;
}

static int
writer_write_bytes(fmt_writer *w, const char *s, Py_ssize_t len)
{
    if (writer_prepare(w, len) < 0)
        return -1;
    memcpy(w->buf + w->pos, s, len);
    w->pos += len;
    return 0;
}

static int
writer_fill(fmt_writer *w, char ch, Py_ssize_t n)
{
    if (writer_prepare(w, n) < 0)
        return -1;
    memset(w->buf + w->pos, ch, n);
    w->pos += n;
    return 0;
}

static int
writer_write_char(fmt_writer *w, Py_UCS4 ch)
{
    char utf8[4];
    int len;

    if (ch < 0x80) {
        utf8[0] = (char)ch;
        len = 1;
    }
    else if (ch < 0x800) {
        utf8[0] = (char)(0xc0 | (ch >> 6));
        utf8[1] = (char)(0x80 | (ch & 0x3f));
        len = 2;
    }
    else if (ch < 0x10000) {
        utf8[0] = (char)(0xe0 | (ch >> 12));
        utf8[1] = (char)(0x80 | ((ch >> 6) & 0x3f));
        utf8[2] = (char)(0x80 | (ch & 0x3f));
        len = 3;
    }
    else {
        utf8[0] = (char)(0xf0 | (ch >> 18));
        utf8[1] = (char)(0x80 | ((ch >> 12) & 0x3f));
        utf8[2] = (char)(0x80 | ((ch >> 6) & 0x3f));
        utf8[3] = (char)(0x80 | (ch & 0x3f));
        len = 4;
    }
    return writer_write_bytes(w, utf8, len);
}

#define F_LJUST (1<<0)
#define F_ZERO  (1<<1)

/* Number of bytes taken by the first `ncodepoints` code points of the
   UTF-8 string s (of nbytes bytes). */
static Py_ssize_t
utf8_prefix_bytes(const char *s, Py_ssize_t nbytes, Py_ssize_t ncodepoints)
{
    Py_ssize_t i = 0;
    while (i < nbytes && ncodepoints > 0) {
        i++;
        while (i < nbytes && ((unsigned char)s[i] & 0xc0) == 0x80)
            i++;
        ncodepoints--;
    }
    return i;
}

static int
writer_write_str(fmt_writer *w, PyObject *str,
                 Py_ssize_t width, Py_ssize_t precision, int flags)
{
    Py_ssize_t length, nbytes, fill;
    const char *utf8;
    PyObject *encoded = NULL;
    int res = -1;

    length = PyUnicode_GET_LENGTH(str);
    utf8 = PyUnicode_AsUTF8AndSize(str, &nbytes);
    if (utf8 == NULL) {
        /* lone surrogates are not valid UTF-8; the result is decoded
           with surrogatepass, so encode them the same way */
        if (!PyErr_ExceptionMatches(PyExc_UnicodeEncodeError))
            return -1;
        PyErr_Clear();
        encoded = PyUnicode_AsEncodedString(str, "utf-8", "surrogatepass");
        if (encoded == NULL)
            return -1;
        utf8 = PyBytes_AS_STRING(encoded);
        nbytes = PyBytes_GET_SIZE(encoded);
    }
    if (precision != -1 && precision < length) {
        nbytes = utf8_prefix_bytes(utf8, nbytes, precision);
        length = precision;
    }
    fill = width > length ? width - length : 0;

    if (fill && !(flags & F_LJUST)) {
        if (writer_fill(w, ' ', fill) < 0)
            goto done;
    }
    if (writer_write_bytes(w, utf8, nbytes) < 0)
        goto done;
    if (fill && (flags & F_LJUST)) {
        if (writer_fill(w, ' ', fill) < 0)
            goto done;
    }
    res = 0;
  done:
    Py_XDECREF(encoded);
    return res;
}

static int
writer_write_cstr(fmt_writer *w, const char *str,
                  Py_ssize_t width, Py_ssize_t precision, int flags)
{
    Py_ssize_t length;
    PyObject *unicode;
    int res;

    if (precision == -1) {
        length = strlen(str);
    }
    else {
        length = 0;
        while (length < precision && str[length]) {
            length++;
        }
    }
    /* decode to validate the bytes and count code points */
    unicode = PyUnicode_DecodeUTF8(str, length, "replace");
    if (unicode == NULL)
        return -1;
    res = writer_write_str(w, unicode, width, -1, flags);
    Py_DECREF(unicode);
    return res;
}

static int
writer_write_wcstr(fmt_writer *w, const wchar_t *str,
                   Py_ssize_t width, Py_ssize_t precision, int flags)
{
    Py_ssize_t length;
    PyObject *unicode;
    int res;

    if (precision == -1) {
        length = wcslen(str);
    }
    else {
        length = 0;
        while (length < precision && str[length]) {
            length++;
        }
    }
    unicode = PyUnicode_FromWideChar(str, length);
    if (unicode == NULL)
        return -1;
    res = writer_write_str(w, unicode, width, -1, flags);
    Py_DECREF(unicode);
    return res;
}

/* maximum number of characters required for output of %jo or %jd or %p.
   We need at most ceil(log8(256)*sizeof(intmax_t)) digits,
   plus 1 for the sign, plus 2 for the 0x prefix (for %p),
   plus 1 for the terminal NUL. */
#define MAX_INTMAX_CHARS (5 + (sizeof(intmax_t)*8-1) / 3)

#define F_LONG 1
#define F_LONGLONG 2
#define F_SIZE 3
#define F_PTRDIFF 4
#define F_INTMAX 5
static const char * const formats[] = {"%d", "%ld", "%lld", "%zd", "%td", "%jd"};
static const char * const formats_o[] = {"%o", "%lo", "%llo", "%zo", "%to", "%jo"};
static const char * const formats_u[] = {"%u", "%lu", "%llu", "%zu", "%tu", "%ju"};
static const char * const formats_x[] = {"%x", "%lx", "%llx", "%zx", "%tx", "%jx"};
static const char * const formats_X[] = {"%X", "%lX", "%llX", "%zX", "%tX", "%jX"};

static const char*
unicode_fromformat_arg(fmt_writer *writer, const char *f, va_list *vargs)
{
    const char *p;
    Py_ssize_t len;
    int flags = 0;
    Py_ssize_t width;
    Py_ssize_t precision;
    int sizemod = 0;

    p = f;
    f++;
    if (*f == '%') {
        if (writer_write_char(writer, '%') < 0)
            return NULL;
        f++;
        return f;
    }

    while (1) {
        switch (*f++) {
        case '-': flags |= F_LJUST; continue;
        case '0': flags |= F_ZERO; continue;
        }
        f--;
        break;
    }

    width = -1;
    if (*f == '*') {
        width = va_arg(*vargs, int);
        if (width < 0) {
            flags |= F_LJUST;
            width = -width;
        }
        f++;
    }
    else if (Py_ISDIGIT((unsigned)*f)) {
        width = *f - '0';
        f++;
        while (Py_ISDIGIT((unsigned)*f)) {
            if (width > (PY_SSIZE_T_MAX - ((int)*f - '0')) / 10) {
                PyErr_SetString(PyExc_ValueError,
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
        if (*f == '*') {
            precision = va_arg(*vargs, int);
            if (precision < 0) {
                precision = -2;
            }
            f++;
        }
        else if (Py_ISDIGIT((unsigned)*f)) {
            precision = (*f - '0');
            f++;
            while (Py_ISDIGIT((unsigned)*f)) {
                if (precision > (PY_SSIZE_T_MAX - ((int)*f - '0')) / 10) {
                    PyErr_SetString(PyExc_ValueError,
                                    "precision too big");
                    return NULL;
                }
                precision = (precision * 10) + (*f - '0');
                f++;
            }
        }
    }

    if (*f == 'l') {
        if (f[1] == 'l') {
            sizemod = F_LONGLONG;
            f += 2;
        }
        else {
            sizemod = F_LONG;
            ++f;
        }
    }
    else if (*f == 'z') {
        sizemod = F_SIZE;
        ++f;
    }
    else if (*f == 't') {
        sizemod = F_PTRDIFF;
        ++f;
    }
    else if (*f == 'j') {
        sizemod = F_INTMAX;
        ++f;
    }

    switch (*f) {
    case 'd': case 'i': case 'o': case 'u': case 'x': case 'X':
        break;
    case 'c': case 'p':
        if (sizemod || width >= 0 || precision >= 0) goto invalid_format;
        break;
    case 's':
    case 'V':
        if (sizemod && sizemod != F_LONG) goto invalid_format;
        break;
    default:
        if (sizemod) goto invalid_format;
        break;
    }

    switch (*f) {
    case 'c':
    {
        int ordinal = va_arg(*vargs, int);
        if (ordinal < 0 || ordinal > 0x10ffff) {
            PyErr_SetString(PyExc_OverflowError,
                            "character argument not in range(0x110000)");
            return NULL;
        }
        if (writer_write_char(writer, ordinal) < 0)
            return NULL;
        break;
    }

    case 'd': case 'i':
    case 'o': case 'u': case 'x': case 'X':
    {
        char buffer[MAX_INTMAX_CHARS];
        const char *fmt = NULL;
        int issigned, sign;
        Py_ssize_t spacepad, zeropad;
        switch (*f) {
            case 'o': fmt = formats_o[sizemod]; break;
            case 'u': fmt = formats_u[sizemod]; break;
            case 'x': fmt = formats_x[sizemod]; break;
            case 'X': fmt = formats_X[sizemod]; break;
            default: fmt = formats[sizemod]; break;
        }
        issigned = (*f == 'd' || *f == 'i');
        switch (sizemod) {
            case F_LONG:
                len = issigned ?
                    sprintf(buffer, fmt, va_arg(*vargs, long)) :
                    sprintf(buffer, fmt, va_arg(*vargs, unsigned long));
                break;
            case F_LONGLONG:
                len = issigned ?
                    sprintf(buffer, fmt, va_arg(*vargs, long long)) :
                    sprintf(buffer, fmt, va_arg(*vargs, unsigned long long));
                break;
            case F_SIZE:
                len = issigned ?
                    sprintf(buffer, fmt, va_arg(*vargs, Py_ssize_t)) :
                    sprintf(buffer, fmt, va_arg(*vargs, size_t));
                break;
            case F_PTRDIFF:
                len = sprintf(buffer, fmt, va_arg(*vargs, ptrdiff_t));
                break;
            case F_INTMAX:
                len = issigned ?
                    sprintf(buffer, fmt, va_arg(*vargs, intmax_t)) :
                    sprintf(buffer, fmt, va_arg(*vargs, uintmax_t));
                break;
            default:
                len = issigned ?
                    sprintf(buffer, fmt, va_arg(*vargs, int)) :
                    sprintf(buffer, fmt, va_arg(*vargs, unsigned int));
                break;
        }
        assert(len >= 0);

        sign = (buffer[0] == '-');
        len -= sign;

        precision = Py_MAX(precision, len);
        width = Py_MAX(width, precision + sign);
        if ((flags & F_ZERO) && !(flags & F_LJUST)) {
            precision = width - sign;
        }

        spacepad = Py_MAX(width - precision - sign, 0);
        zeropad = Py_MAX(precision - len, 0);

        if (spacepad && !(flags & F_LJUST)) {
            if (writer_fill(writer, ' ', spacepad) < 0)
                return NULL;
        }
        if (sign) {
            if (writer_write_bytes(writer, "-", 1) < 0)
                return NULL;
        }
        if (zeropad) {
            if (writer_fill(writer, '0', zeropad) < 0)
                return NULL;
        }
        if (writer_write_bytes(writer, &buffer[sign], len) < 0)
            return NULL;
        if (spacepad && (flags & F_LJUST)) {
            if (writer_fill(writer, ' ', spacepad) < 0)
                return NULL;
        }
        break;
    }

    case 'p':
    {
        char number[MAX_INTMAX_CHARS];

        len = sprintf(number, "%p", va_arg(*vargs, void*));
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

        if (writer_write_bytes(writer, number, len) < 0)
            return NULL;
        break;
    }

    case 's':
    {
        if (sizemod) {
            const wchar_t *s = va_arg(*vargs, const wchar_t*);
            if (writer_write_wcstr(writer, s, width, precision, flags) < 0)
                return NULL;
        }
        else {
            const char *s = va_arg(*vargs, const char*);
            if (writer_write_cstr(writer, s, width, precision, flags) < 0)
                return NULL;
        }
        break;
    }

    case 'U':
    {
        PyObject *obj = va_arg(*vargs, PyObject *);
        assert(obj && PyUnicode_Check(obj));

        if (writer_write_str(writer, obj, width, precision, flags) == -1)
            return NULL;
        break;
    }

    case 'V':
    {
        PyObject *obj = va_arg(*vargs, PyObject *);
        const char *str = NULL;
        const wchar_t *wstr = NULL;
        if (sizemod) {
            wstr = va_arg(*vargs, const wchar_t*);
        }
        else {
            str = va_arg(*vargs, const char *);
        }
        if (obj) {
            assert(PyUnicode_Check(obj));
            if (writer_write_str(writer, obj, width, precision, flags) == -1)
                return NULL;
        }
        else if (sizemod) {
            assert(wstr != NULL);
            if (writer_write_wcstr(writer, wstr, width, precision, flags) < 0)
                return NULL;
        }
        else {
            assert(str != NULL);
            if (writer_write_cstr(writer, str, width, precision, flags) < 0)
                return NULL;
        }
        break;
    }

    case 'S':
    {
        PyObject *obj = va_arg(*vargs, PyObject *);
        PyObject *str;
        assert(obj);
        str = PyObject_Str(obj);
        if (!str)
            return NULL;
        if (writer_write_str(writer, str, width, precision, flags) == -1) {
            Py_DECREF(str);
            return NULL;
        }
        Py_DECREF(str);
        break;
    }

    case 'R':
    {
        PyObject *obj = va_arg(*vargs, PyObject *);
        PyObject *repr;
        assert(obj);
        repr = PyObject_Repr(obj);
        if (!repr)
            return NULL;
        if (writer_write_str(writer, repr, width, precision, flags) == -1) {
            Py_DECREF(repr);
            return NULL;
        }
        Py_DECREF(repr);
        break;
    }

    case 'A':
    {
        PyObject *obj = va_arg(*vargs, PyObject *);
        PyObject *ascii;
        assert(obj);
        ascii = PyObject_ASCII(obj);
        if (!ascii)
            return NULL;
        if (writer_write_str(writer, ascii, width, precision, flags) == -1) {
            Py_DECREF(ascii);
            return NULL;
        }
        Py_DECREF(ascii);
        break;
    }

    default:
    invalid_format:
        PyErr_Format(PyExc_SystemError, "invalid format string: %s", p);
        return NULL;
    }

    f++;
    return f;
}

PyObject *
PyUnicode_FromFormatV(const char *format, va_list vargs)
{
    va_list vargs2;
    const char *f;
    fmt_writer writer;
    PyObject *result;

    writer.buf = NULL;
    writer.pos = 0;
    writer.size = 0;
    if (writer_prepare(&writer, strlen(format) + 100) < 0)
        return NULL;

    va_copy(vargs2, vargs);

    for (f = format; *f; ) {
        if (*f == '%') {
            f = unicode_fromformat_arg(&writer, f, &vargs2);
            if (f == NULL)
                goto fail;
        }
        else {
            const char *p;
            Py_ssize_t len;

            p = f;
            do
            {
                if ((unsigned char)*p > 127) {
                    PyErr_Format(PyExc_ValueError,
                        "PyUnicode_FromFormatV() expects an ASCII-encoded format "
                        "string, got a non-ASCII byte: 0x%02x",
                        (unsigned char)*p);
                    goto fail;
                }
                p++;
            }
            while (*p != '\0' && *p != '%');
            len = p - f;

            if (writer_write_bytes(&writer, f, len) < 0)
                goto fail;

            f = p;
        }
    }
    va_end(vargs2);
    /* surrogatepass: %c accepts lone surrogate ordinals */
    result = PyUnicode_DecodeUTF8(writer.buf, writer.pos, "surrogatepass");
    PyMem_Free(writer.buf);
    return result;

  fail:
    va_end(vargs2);
    PyMem_Free(writer.buf);
    return NULL;
}

PyObject *
PyUnicode_FromFormat(const char *format, ...)
{
    PyObject* ret;
    va_list vargs;

    va_start(vargs, format);
    ret = PyUnicode_FromFormatV(format, vargs);
    va_end(vargs);
    return ret;
}
