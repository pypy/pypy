
#include "Python.h"
static void
makefmt(char *fmt, int longflag, int size_tflag, int zeropad, int width, int precision, char c)
{
    *fmt++ = '%';
    if (width) {
        if (zeropad)
            *fmt++ = '0';
        fmt += sprintf(fmt, "%d", width);
    }
    if (precision)
        fmt += sprintf(fmt, ".%d", precision);
    if (longflag)
        *fmt++ = 'l';
    else if (size_tflag) {
        char *f = PY_FORMAT_SIZE_T;
        while (*f)
            *fmt++ = *f++;
    }
    *fmt++ = c;
    *fmt = '\0';
}

#define appendstring(string) \
    do { \
        for (copy = string;*copy; copy++) { \
            *s++ = (unsigned char)*copy; \
        } \
    } while (0)


PyObject *
PyUnicode_FromFormatV(const char *format, va_list vargs)
{
    va_list count;
    Py_ssize_t callcount = 0;
    PyObject **callresults = NULL;
    PyObject **callresult = NULL;
    Py_ssize_t n = 0;
    int width = 0;
    int precision = 0;
    int zeropad;
    const char* f;
    Py_UNICODE *s;
    PyObject *string;
    /* used by sprintf */
    char buffer[21];
    /* use abuffer instead of buffer, if we need more space
     * (which can happen if there's a format specifier with width). */
    char *abuffer = NULL;
    char *realbuffer;
    Py_ssize_t abuffersize = 0;
    char fmt[60]; /* should be enough for %0width.precisionld */
    const char *copy;

#ifdef VA_LIST_IS_ARRAY
    Py_MEMCPY(count, vargs, sizeof(va_list));
#else
#ifdef  __va_copy
    __va_copy(count, vargs);
#else
    count = vargs;
#endif
#endif
     /* step 1: count the number of %S/%R/%s format specifications
      * (we call PyObject_Str()/PyObject_Repr()/PyUnicode_DecodeUTF8() for these
      * objects once during step 3 and put the result in an array) */
    for (f = format; *f; f++) {
         if (*f == '%') {
             f++;
             while (*f && *f != '%' && !isalpha((unsigned)*f))
                 f++;
             if (!*f)
                 break;
             if (*f == 's' || *f=='S' || *f=='R')
                 ++callcount;
         }
    }
    /* step 2: allocate memory for the results of
     * PyObject_Str()/PyObject_Repr()/PyUnicode_DecodeUTF8() calls */
    if (callcount) {
        callresults = PyObject_Malloc(sizeof(PyObject *)*callcount);
        if (!callresults) {
            PyErr_NoMemory();
            return NULL;
        }
        callresult = callresults;
    }
    /* step 3: figure out how large a buffer we need */
    for (f = format; *f; f++) {
        if (*f == '%') {
            const char* p = f++;
            width = 0;
            while (isdigit((unsigned)*f))
                width = (width*10) + *f++ - '0';
            precision = 0;
            if (*f == '.') {
                f++;
                while (isdigit((unsigned)*f))
                    precision = (precision*10) + *f++ - '0';
            }

            /* skip the 'l' or 'z' in {%ld, %zd, %lu, %zu} since
             * they don't affect the amount of space we reserve.
             */
            if ((*f == 'l' || *f == 'z') &&
                (f[1] == 'd' || f[1] == 'u'))
                ++f;

            switch (*f) {
            case 'c':
            {
                int ordinal = va_arg(count, int);
#ifdef Py_UNICODE_WIDE
                if (ordinal < 0 || ordinal > 0x10ffff) {
                    PyErr_SetString(PyExc_OverflowError,
                                    "%c arg not in range(0x110000) "
                                    "(wide Python build)");
                    goto fail;
                }
#else
                if (ordinal < 0 || ordinal > 0xffff) {
                    PyErr_SetString(PyExc_OverflowError,
                                    "%c arg not in range(0x10000) "
                                    "(narrow Python build)");
                    goto fail;
                }
#endif
                /* fall through... */
            }
            case '%':
                n++;
                break;
            case 'd': case 'u': case 'i': case 'x':
                (void) va_arg(count, int);
                if (width < precision)
                    width = precision;
                /* 20 bytes is enough to hold a 64-bit
                   integer.  Decimal takes the most space.
                   This isn't enough for octal.
                   If a width is specified we need more
                   (which we allocate later). */
                if (width < 20)
                    width = 20;
                n += width;
                if (abuffersize < width)
                    abuffersize = width;
                break;
            case 's':
            {
                /* UTF-8 */
                const char *s = va_arg(count, const char*);
                PyObject *str = PyUnicode_DecodeUTF8(s, strlen(s), "replace");
                if (!str)
                    goto fail;
                n += PyUnicode_GET_SIZE(str);
                /* Remember the str and switch to the next slot */
                *callresult++ = str;
                break;
            }
            case 'U':
            {
                PyObject *obj = va_arg(count, PyObject *);
                assert(obj && PyUnicode_Check(obj));
                n += PyUnicode_GET_SIZE(obj);
                break;
            }
            case 'V':
            {
                PyObject *obj = va_arg(count, PyObject *);
                const char *str = va_arg(count, const char *);
                assert(obj || str);
                assert(!obj || PyUnicode_Check(obj));
                if (obj)
                    n += PyUnicode_GET_SIZE(obj);
                else
                    n += strlen(str);
                break;
            }
            case 'S':
            {
                PyObject *obj = va_arg(count, PyObject *);
                PyObject *str;
                assert(obj);
                str = PyObject_Str(obj);
                if (!str)
                    goto fail;
                n += PyString_GET_SIZE(str);
                /* Remember the str and switch to the next slot */
                *callresult++ = str;
                break;
            }
            case 'R':
            {
                PyObject *obj = va_arg(count, PyObject *);
                PyObject *repr;
                assert(obj);
                repr = PyObject_Repr(obj);
                if (!repr)
                    goto fail;
                n += PyUnicode_GET_SIZE(repr);
                /* Remember the repr and switch to the next slot */
                *callresult++ = repr;
                break;
            }
            case 'p':
                (void) va_arg(count, int);
                /* maximum 64-bit pointer representation:
                 * 0xffffffffffffffff
                 * so 19 characters is enough.
                 * XXX I count 18 -- what's the extra for?
                 */
                n += 19;
                break;
            default:
                /* if we stumble upon an unknown
                   formatting code, copy the rest of
                   the format string to the output
                   string. (we cannot just skip the
                   code, since there's no way to know
                   what's in the argument list) */
                n += strlen(p);
                goto expand;
            }
        } else
            n++;
    }
  expand:
    if (abuffersize > 20) {
        /* add 1 for sprintf's trailing null byte */
        abuffer = PyObject_Malloc(abuffersize + 1);
        if (!abuffer) {
            PyErr_NoMemory();
            goto fail;
        }
        realbuffer = abuffer;
    }
    else
        realbuffer = buffer;
    /* step 4: fill the buffer */
    /* Since we've analyzed how much space we need for the worst case,
       we don't have to resize the string.
       There can be no errors beyond this point. */
    string = PyUnicode_FromUnicode(NULL, n);
    if (!string)
        goto fail;

    s = PyUnicode_AS_UNICODE(string);
    callresult = callresults;

    for (f = format; *f; f++) {
        if (*f == '%') {
            const char* p = f++;
            int longflag = 0;
            int size_tflag = 0;
            zeropad = (*f == '0');
            /* parse the width.precision part */
            width = 0;
            while (isdigit((unsigned)*f))
                width = (width*10) + *f++ - '0';
            precision = 0;
            if (*f == '.') {
                f++;
                while (isdigit((unsigned)*f))
                    precision = (precision*10) + *f++ - '0';
            }
            /* handle the long flag, but only for %ld and %lu.
               others can be added when necessary. */
            if (*f == 'l' && (f[1] == 'd' || f[1] == 'u')) {
                longflag = 1;
                ++f;
            }
            /* handle the size_t flag. */
            if (*f == 'z' && (f[1] == 'd' || f[1] == 'u')) {
                size_tflag = 1;
                ++f;
            }

            switch (*f) {
            case 'c':
                *s++ = va_arg(vargs, int);
                break;
            case 'd':
                makefmt(fmt, longflag, size_tflag, zeropad, width, precision, 'd');
                if (longflag)
                    sprintf(realbuffer, fmt, va_arg(vargs, long));
                else if (size_tflag)
                    sprintf(realbuffer, fmt, va_arg(vargs, Py_ssize_t));
                else
                    sprintf(realbuffer, fmt, va_arg(vargs, int));
                appendstring(realbuffer);
                break;
            case 'u':
                makefmt(fmt, longflag, size_tflag, zeropad, width, precision, 'u');
                if (longflag)
                    sprintf(realbuffer, fmt, va_arg(vargs, unsigned long));
                else if (size_tflag)
                    sprintf(realbuffer, fmt, va_arg(vargs, size_t));
                else
                    sprintf(realbuffer, fmt, va_arg(vargs, unsigned int));
                appendstring(realbuffer);
                break;
            case 'i':
                makefmt(fmt, 0, 0, zeropad, width, precision, 'i');
                sprintf(realbuffer, fmt, va_arg(vargs, int));
                appendstring(realbuffer);
                break;
            case 'x':
                makefmt(fmt, 0, 0, zeropad, width, precision, 'x');
                sprintf(realbuffer, fmt, va_arg(vargs, int));
                appendstring(realbuffer);
                break;
            case 's':
            {
                /* unused, since we already have the result */
                (void) va_arg(vargs, char *);
                Py_UNICODE_COPY(s, PyUnicode_AS_UNICODE(*callresult),
                                PyUnicode_GET_SIZE(*callresult));
                s += PyUnicode_GET_SIZE(*callresult);
                /* We're done with the unicode()/repr() => forget it */
                Py_DECREF(*callresult);
                /* switch to next unicode()/repr() result */
                ++callresult;
                break;
            }
            case 'U':
            {
                PyObject *obj = va_arg(vargs, PyObject *);
                Py_ssize_t size = PyUnicode_GET_SIZE(obj);
                Py_UNICODE_COPY(s, PyUnicode_AS_UNICODE(obj), size);
                s += size;
                break;
            }
            case 'V':
            {
                PyObject *obj = va_arg(vargs, PyObject *);
                const char *str = va_arg(vargs, const char *);
                if (obj) {
                    Py_ssize_t size = PyUnicode_GET_SIZE(obj);
                    Py_UNICODE_COPY(s, PyUnicode_AS_UNICODE(obj), size);
                    s += size;
                } else {
                    appendstring(str);
                }
                break;
            }
            case 'S':
            case 'R':
            {
                const char *str = PyString_AS_STRING(*callresult);
                /* unused, since we already have the result */
                (void) va_arg(vargs, PyObject *);
                appendstring(str);
                /* We're done with the unicode()/repr() => forget it */
                Py_DECREF(*callresult);
                /* switch to next unicode()/repr() result */
                ++callresult;
                break;
            }
            case 'p':
                sprintf(buffer, "%p", va_arg(vargs, void*));
                /* %p is ill-defined:  ensure leading 0x. */
                if (buffer[1] == 'X')
                    buffer[1] = 'x';
                else if (buffer[1] != 'x') {
                    memmove(buffer+2, buffer, strlen(buffer)+1);
                    buffer[0] = '0';
                    buffer[1] = 'x';
                }
                appendstring(buffer);
                break;
            case '%':
                *s++ = '%';
                break;
            default:
                appendstring(p);
                goto end;
            }
        } else
            *s++ = *f;
    }

  end:
    if (callresults)
        PyObject_Free(callresults);
    if (abuffer)
        PyObject_Free(abuffer);
    PyUnicode_Resize(&string, s - PyUnicode_AS_UNICODE(string));
    return string;
  fail:
    if (callresults) {
        PyObject **callresult2 = callresults;
        while (callresult2 < callresult) {
            Py_DECREF(*callresult2);
            ++callresult2;
        }
        PyObject_Free(callresults);
    }
    if (abuffer)
        PyObject_Free(abuffer);
    return NULL;
}

#undef appendstring

PyObject *
PyUnicode_FromFormat(const char *format, ...)
{
    PyObject* ret;
    va_list vargs;

#ifdef HAVE_STDARG_PROTOTYPES
    va_start(vargs, format);
#else
    va_start(vargs);
#endif
    ret = PyUnicode_FromFormatV(format, vargs);
    va_end(vargs);
    return ret;
}


