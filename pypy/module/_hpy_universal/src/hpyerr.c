#include <src/exception.h>
#include "universal/hpy.h"
#include "hpyerr.h"
#include "bridge.h"

#ifndef RPYTHON_LL2CTYPES
#  include "common_header.h"
#  include "preimpl.h"
#endif


int pypy_HPyErr_Occurred(HPyContext ctx)
{
#ifdef RPYTHON_LL2CTYPES
    /* before translation */
    return hpy_err_occurred_rpy();
#else
    /* after translation */
    return RPyExceptionOccurred();
#endif
}

/*
void pypy_hpy_Err_Clear(void)
{
    RPyClearException();
}
*/
