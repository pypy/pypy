#include "common_header.h"
#include "preimpl.h"
#include <src/exception.h>
#include "universal/hpy.h"
#include "hpyerr.h"

/* these are helper functions which are called by interp_hpyerr.py */

int pypy_hpy_Err_Occurred(void)
{
    return RPyExceptionOccurred();
}

void pypy_hpy_Err_Clear(void)
{
    RPyClearException();
}
