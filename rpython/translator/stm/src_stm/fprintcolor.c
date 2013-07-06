/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"


void stm_fatalerror(const char *format, ...)
{
    va_list ap;

#ifdef _GC_DEBUGPRINTS
    dprintf(("STM Subsystem: Fatal Error\n"));
#else
    fprintf(stderr, "STM Subsystem: Fatal Error\n");
#endif

    va_start(ap, format);
    vfprintf(stderr, format, ap);
    va_end(ap);

    abort();
}


#ifdef _GC_DEBUGPRINTS

static __thread revision_t tcolor = 0;
static revision_t tnextid = 0;

int dprintfcolor(void)
{
    if (tcolor == 0) {
        while (1) {
            tcolor = tnextid;
            if (bool_cas(&tnextid, tcolor, tcolor + 1))
                break;
        }
        tcolor = 31 + tcolor % 6;
    }
    return tcolor;
}

int threadcolor_printf(const char *format, ...)
{
    char buffer[2048];
    va_list ap;
    int result;
    int size = (int)sprintf(buffer, "\033[%dm", dprintfcolor());
    assert(size >= 0);

    va_start(ap, format);
    result = vsnprintf(buffer + size, 2000, format, ap);
    assert(result >= 0);
    va_end(ap);

    strcpy(buffer + size + result, "\033[0m");
    fputs(buffer, stderr);

    return result;
}

#endif
