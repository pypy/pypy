#include "universal/hpy.h"

#include <stdio.h>

/* XXX: this function is copied&pasted THREE times:
 *     hpy_devel/include/hpy.h
 *     cpython-universal/api.c
 *     pypy/module/hpy_universal/src/getargs.c
 *
 * We need a way to share this kind of common code
 */

/* would be nice if this were static :( */
int
ctx_Arg_Parse(HPyContext ctx, HPy *args, HPy_ssize_t nargs,
              const char *fmt, va_list vl)
{
    const char *fmt1 = fmt;
    HPy_ssize_t i = 0;

    while (*fmt1 != 0) {
        if (i >= nargs) {
            abort(); // XXX
        }
        switch (*fmt1++) {
        case 'l': {
            long *output = va_arg(vl, long *);
            long value = HPyLong_AsLong(ctx, args[i]);
            // XXX check for exceptions
            *output = value;
            break;
        }
        default:
            abort();  // XXX
        }
        i++;
    }
    if (i != nargs) {
        abort();   // XXX
    }

    return 1;
}
