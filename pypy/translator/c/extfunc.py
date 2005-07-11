import types
from pypy.rpython import lltype
from pypy.translator.c.support import cdecl
from pypy.rpython.rmodel import getfunctionptr
from pypy.rpython.rstr import STR
from pypy.rpython.module import ll_os, ll_time


# table of functions hand-written in src/ll_*.h
EXTERNALS = {
    ll_os  .ll_os_open:    'LL_os_open',
    ll_os  .ll_read_into:  'LL_read_into',
    ll_os  .ll_os_write:   'LL_os_write',
    ll_os  .ll_os_close:   'LL_os_close',
    ll_os  .ll_os_dup:     'LL_os_dup',
    ll_os  .ll_os_getcwd:  'LL_os_getcwd',
    ll_time.ll_time_clock: 'LL_time_clock',
    }


def predeclare_common_types(db, rtyper):
    # Common types
    yield ('RPyString', STR)


def predeclare_utility_functions(db, rtyper):
    # Common utility functions
    def RPyString_New(length=lltype.Signed):
        return lltype.malloc(STR, length)

    for fname, f in locals().items():
        if isinstance(f, types.FunctionType):
            # hack: the defaults give the type of the arguments
            fptr = rtyper.annotate_helper(f, f.func_defaults)
            yield (fname, fptr)


def predeclare_extfuncs(db, rtyper):
    for func, funcobj in db.externalfuncs.items():
        c_name = EXTERNALS[func]
        funcptr = lltype._ptr(lltype.Ptr(lltype.typeOf(funcobj)), funcobj) # hum
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
        exc_llvalue = exceptiondata.ll_pyexcclass2exc(
            lltype.pyobjectptr(pyexccls))
        # strange naming here because the macro name must be
        # a substring of PyExc_%s
        yield ('Exc_%s' % pyexccls.__name__, exc_llvalue)


def predeclare_all(db, rtyper):
    for fn in [predeclare_common_types,
               predeclare_utility_functions,
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

    yield '#define HAVE_RTYPER'
    decls = list(predeclare_all(db, rtyper))

    # the following line must be done after all predeclare_xxx(), to specialize
    # the functions created by annotate_helper() above.  But it must be done
    # before db.get(), to ensure that the database only sees specialized blocks.
    rtyper.specialize_more_blocks()

    for c_name, obj in decls:
        if isinstance(obj, lltype.LowLevelType):
            yield predeclaretype(c_name, obj)
        elif isinstance(obj, types.FunctionType):
            yield predeclarefn(c_name, obj)
        else:
            yield predeclare(c_name, obj)

    db.complete()   # because of the get() and gettype() above
