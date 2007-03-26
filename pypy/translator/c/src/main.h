
#ifndef STANDALONE_ENTRY_POINT
#  define STANDALONE_ENTRY_POINT   PYPY_STANDALONE
#endif

char *RPython_StartupCode(void);  /* forward */


/* prototypes */

int main(int argc, char *argv[]);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

int main(int argc, char *argv[])
{
    char *errmsg;
    int i, exitcode;
    RPyListOfString *list;

    instrument_setup();

    errmsg = RPython_StartupCode();
    if (errmsg) goto error;

    list = _RPyListOfString_New(argc);
    if (RPyExceptionOccurred()) goto memory_out;
    for (i=0; i<argc; i++) {
        RPyString *s = RPyString_FromString(argv[i]);
        if (RPyExceptionOccurred()) goto memory_out;
        _RPyListOfString_SetItem(list, i, s);
    }

    exitcode = STANDALONE_ENTRY_POINT(list);
    if (RPyExceptionOccurred()) {
        /* fish for the exception type, at least */
#ifndef AVR
        fprintf(stderr, "Fatal RPython error: %s\n",
                RPyFetchExceptionType()->ov_name->items);
#endif
        exitcode = 1;
    }
    return exitcode;

 memory_out:
    errmsg = "out of memory";
 error:
#ifndef AVR
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
#endif
    return 1;
}

#endif /* PYPY_NOT_MAIN_FILE */
