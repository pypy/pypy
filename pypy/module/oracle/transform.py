from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.oracle import roci, config

def OracleNumberToPythonFloat(environment, valueptr):
    "Return a Python float object given an oracle number"
    doubleptr = lltype.malloc(roci.Ptr(rffi.DOUBLE).TO, 1, flavor='raw')
    try:
        status = roci.OCINumberToReal(
            environment.errorHandle,
            valueptr,
            rffi.sizeof(rffi.DOUBLE),
            rffi.cast(roci.dvoidp, doubleptr))
        environment.checkForError(status, "OracleNumberToPythonFloat()")
        return environment.space.wrap(doubleptr[0])
    finally:
        lltype.free(doubleptr, flavor='raw')

def OracleDateToPythonDate(environment, valueptr):
    print valueptr.OCIDateYYYY, valueptr.OCIDateMM, valueptr.OCIDateDD
    yearptr = lltype.malloc(roci.Ptr(roci.sb2).TO, 1, flavor='raw')
    monthptr = lltype.malloc(roci.Ptr(roci.ub1).TO, 1, flavor='raw')
    dayptr = lltype.malloc(roci.Ptr(roci.ub1).TO, 1, flavor='raw')

    try:
        roci.OCIDateGetDate(
            valueptr,
            yearptr,
            monthptr,
            dayptr)

        space = environment.space
        w = space.wrap

        return space.call_w(w_date, [w(yearptr[0]), w(monthptr[0]), w(dayptr[0])])
    finally:
        lltype.free(yearptr, flavor='raw')
        lltype.free(monthptr, flavor='raw')
        lltype.free(dayptr, flavor='raw')

def OracleDateToPythonDateTime(environment, valueptr):
    space = environment.space
    w = space.wrap

    # XXX check that this does not copy the whole structure
    date = valueptr[0]
    time = date.c_OCIDateTime

    w_datetime = space.getattr(
        space.getbuiltinmodule('datetime'),
        w('datetime'))

    return space.call_function(
        w_datetime,
        w(date.c_OCIDateYYYY),
        w(date.c_OCIDateMM),
        w(date.c_OCIDateDD),
        w(time.c_OCITimeHH),
        w(time.c_OCITimeMI),
        w(time.c_OCITimeSS))

