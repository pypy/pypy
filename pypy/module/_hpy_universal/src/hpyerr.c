#ifndef RPYTHON_LL2CTYPES
#  include "common_header.h"
#  include "structdef.h"
#  include "forwarddecl.h"
#  include "preimpl.h"
#  include "src/exception.h"
#endif

#include "universal/hpy.h"
#include "hpyerr.h"
#include "bridge.h"



int pypy_HPyErr_Occurred(HPyContext ctx)
{
#ifdef RPYTHON_LL2CTYPES
    /* before translation */
    return hpy_err_Occurred_rpy();
#else
    /* after translation */
    return RPyExceptionOccurred();
#endif
}

void pypy_HPyErr_SetString(HPyContext ctx, HPy type, const char *message)
{
#ifndef RPYTHON_LL2CTYPES /* after translation */
    // it is allowed to call this function with an exception set: for now, we
    // just ensure that the exception is cleared before setting it again in
    // hpy_err_SetString. In the future, we might have to add some logic for
    // chaining exceptions.
    RPyClearException();
#endif
    hpy_err_SetString(ctx, type, message);
}
