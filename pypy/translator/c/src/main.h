
#define STANDALONE_ENTRY_POINT   PYPY_STANDALONE

char *RPython_StartupCode(void);  /* forward */


int main(int argc, char *argv[])
{
    char *errmsg = "out of memory";
    int i;
    RPyListOfString *list;
    errmsg = RPython_StartupCode();
    if (errmsg) goto error;

    list = _RPyListOfString_New(argc);
    if (RPyExceptionOccurred()) goto error;
    for (i=0; i<argc; i++) {
        RPyString *s = RPyString_FromString(argv[i]);
        if (RPyExceptionOccurred()) goto error;
        _RPyListOfString_SetItem(list, i, s);
    }


    return STANDALONE_ENTRY_POINT(list);

 error:
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
    return 1;
}
