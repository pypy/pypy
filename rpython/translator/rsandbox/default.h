/*** translator/rsandbox/default.h ***/


/* This is called by most default implementations of 'rsandbox_*' */
__attribute__((noinline, noreturn))
static void rsand_fatal(const char *fnname)
{
    fprintf(stderr, "The sandboxed program called the C function %s(), "
            "but no implementation of this function was provided.\n",
            fnname);
    abort();
}


/* Default implementation for some functions that don't abort */

static char *rsand_def_getenv(char *v)
{
    /* default implementation: "no such environment variable" */
    return NULL;
}


/*** generated code follows ***/
