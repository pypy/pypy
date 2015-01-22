/* Imported by rpython/translator/stm/import_stmgc.py */
/* ------------------------------------------------------------ */
#ifdef STM_DEBUGPRINT
/* ------------------------------------------------------------ */


static int threadcolor_printf(const char *format, ...)
{
    char buffer[2048];
    va_list ap;
    int result;
    int size = (int)sprintf(buffer, "\033[%dm[%d,%d,%lx] ",
                            dprintfcolor(), STM_SEGMENT->segment_num,
                            (int)getpid(), (long)pthread_self());
    assert(size >= 0);

    va_start(ap, format);
    result = vsnprintf(buffer + size, 2000, format, ap);
    assert(result >= 0);
    va_end(ap);

    strcpy(buffer + size + result, "\033[0m");
    fputs(buffer, stderr);

    return result;
}


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */


static void stm_fatalerror(const char *format, ...)
{
    va_list ap;

#ifdef STM_DEBUGPRINT
    dprintf(("STM Subsystem: Fatal Error\n"));
#else
    fprintf(stderr, "STM Subsystem: Fatal Error\n");
#endif

    va_start(ap, format);
    vfprintf(stderr, format, ap);
    fprintf(stderr, "\n");
    va_end(ap);

    abort();
}
