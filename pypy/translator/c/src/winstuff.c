
/************************************************************/
 /*****  Windows-specific stuff.                         *****/


/* copied from CPython. */

#if defined _MSC_VER && _MSC_VER >= 1400 && defined(__STDC_SECURE_LIB__)
/* crt variable checking in VisualStudio .NET 2005 */
#include <crtdbg.h>

/* Invalid parameter handler.  Sets a ValueError exception */
static void
InvalidParameterHandler(
    const wchar_t * expression,
    const wchar_t * function,
    const wchar_t * file,
    unsigned int line,
    uintptr_t pReserved)
{
    /* Do nothing, allow execution to continue.  Usually this
     * means that the CRT will set errno to EINVAL
     */
}
#endif


void pypy_Windows_startup(void)
{
#if 0 &&defined _MSC_VER && _MSC_VER >= 1400 && defined(__STDC_SECURE_LIB__)
    /* Set CRT argument error handler */
    _set_invalid_parameter_handler(InvalidParameterHandler);
    /* turn off assertions within CRT in debug mode;
       instead just return EINVAL */
    _CrtSetReportMode(_CRT_ASSERT, 0);
#endif
}
