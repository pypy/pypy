import types
from pypy.rpython.lltype import Ptr, pyobjectptr, LowLevelType, _ptr, typeOf
from pypy.translator.c.support import cdecl
from pypy.rpython.rmodel import getfunctionptr
from pypy.rpython.rstr import STR
from pypy.rpython import extfunctable


# table of functions hand-written in extfunc_include.h
EXTERNALS = {
    extfunctable.ll_os_open:    'LL_os_open',
    extfunctable.ll_time_clock: 'LL_time_clock',
    }


def predeclare_common_types(db, rtyper):
    # Common types
    yield ('RPyString', STR)


def predeclare_extfuncs(db, rtyper):
    for func, funcobj in db.externalfuncs.items():
        c_name = EXTERNALS[func]
        funcptr = _ptr(Ptr(typeOf(funcobj)), funcobj)   # hum
        yield c_name, funcptr


def predeclare_exception_data(db, rtyper):
    # Exception-related types and constants
    exceptiondata = rtyper.getexceptiondata()

    yield ('RPYTHON_EXCEPTION_VTABLE', exceptiondata.lltype_of_exception_type)
    yield ('RPYTHON_EXCEPTION',        exceptiondata.lltype_of_exception_value)

    yield ('RPYTHON_EXCEPTION_MATCH',  exceptiondata.ll_exception_match)
    yield ('RPYTHON_TYPE_OF_EXC_INST', exceptiondata.ll_type_of_exc_inst)
    yield ('RPYTHON_PYEXCCLASS2EXC',   exceptiondata.ll_pyexcclass2exc)
    yield ('RAISE_OSERROR',            exceptiondata.ll_raise_OSError)

    for pyexccls in exceptiondata.standardexceptions:
        exc_llvalue = exceptiondata.ll_pyexcclass2exc(pyobjectptr(pyexccls))
        # strange naming here because the macro name must be
        # a substring of PyExc_%s
        yield ('Exc_%s' % pyexccls.__name__, exc_llvalue)


def predeclare_all(db, rtyper):
    for fn in [predeclare_common_types,
               predeclare_exception_data,
               predeclare_extfuncs,
               ]:
        for t in fn(db, rtyper):
            yield t

# ____________________________________________________________

def pre_include_code_lines(db, rtyper):
    # generate some #defines that go before the #include to provide
    # predeclared well-known names for constant objects, functions and
    # types.  These names are then used by the #included files, like
    # g_exception.h.

    def predeclare(c_name, lowlevelobj):
        llname = db.get(lowlevelobj)
        assert '\n' not in llname
        return '#define\t%s\t%s' % (c_name, llname)

    def predeclarefn(c_name, ll_func):
        return predeclare(c_name, getfunctionptr(db.translator, ll_func))

    def predeclaretype(c_typename, lowleveltype):
        typename = db.gettype(lowleveltype)
        return 'typedef %s;' % cdecl(typename, c_typename)

    for c_name, obj in predeclare_all(db, rtyper):
        if isinstance(obj, LowLevelType):
            yield predeclaretype(c_name, obj)
        elif isinstance(obj, types.FunctionType):
            yield predeclarefn(c_name, obj)
        else:
            yield predeclare(c_name, obj)

    db.complete()   # because of the get() and gettype() above
