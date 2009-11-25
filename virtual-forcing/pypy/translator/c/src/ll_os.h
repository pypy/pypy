/************************************************************/
 /***  C header subsection: os module                      ***/

/* NOTE NOTE NOTE: This whole file is going away...
*/

static int geterrno(void)    /* XXX only for rpython.rctypes, kill me */
{
    return errno;
}
