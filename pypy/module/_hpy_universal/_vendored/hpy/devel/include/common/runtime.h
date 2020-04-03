/*
    HPy helper functions provided by the HPy runtime library.
*/

HPyAPI_RUNTIME_FUNC(int)
HPyArg_Parse(HPyContext ctx, HPy *args, HPy_ssize_t nargs, const char *fmt, ...);

HPyAPI_RUNTIME_FUNC(int)
HPyArg_ParseKeywords(HPyContext ctx, HPy *args, HPy_ssize_t nargs, HPy kw,
                     const char *fmt, const char *keywords[], ...);
