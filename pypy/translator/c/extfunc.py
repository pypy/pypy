import types
from pypy.rpython import lltype
from pypy.translator.c.support import cdecl
from pypy.rpython.rmodel import getfunctionptr
from pypy.rpython.rstr import STR
from pypy.rpython.module import ll_os, ll_time, ll_math


# table of functions hand-written in src/ll_*.h
EXTERNALS = {
    ll_os  .ll_os_open:    'LL_os_open',
    ll_os  .ll_read_into:  'LL_read_into',
    ll_os  .ll_os_write:   'LL_os_write',
    ll_os  .ll_os_close:   'LL_os_close',
    ll_os  .ll_os_dup:     'LL_os_dup',
    ll_os  .ll_os_getcwd:  'LL_os_getcwd',
    ll_os  .ll_os_stat:    'LL_os_stat',
    ll_os  .ll_os_fstat:   'LL_os_fstat',
    ll_os  .ll_os_lseek:   'LL_os_lseek',
    ll_os  .ll_os_isatty:  'LL_os_isatty',
    ll_time.ll_time_clock: 'LL_time_clock',
    ll_time.ll_time_sleep: 'LL_time_sleep',
    ll_time.ll_time_time:  'LL_time_time',
    ll_math.ll_math_frexp: 'LL_math_frexp',
    ll_math.ll_math_atan2: 'LL_math_atan2',
    ll_math.ll_math_fmod : 'LL_math_fmod',
    ll_math.ll_math_ldexp: 'LL_math_ldexp',
    ll_math.ll_math_modf:  'LL_math_modf',
    ll_math.ll_math_hypot: 'LL_math_hypot',
    }

#______________________________________________________
# insert 'simple' math functions into EXTERNALs table:

simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

for name in simple_math_functions:
    EXTERNALS[getattr(ll_math, 'll_math_%s' % name)] = 'LL_math_%s' % name

#______________________________________________________


def predeclare_common_types(db, rtyper):
    # Common types
    yield ('RPyString', STR)
    yield ('RPyFREXP_RESULT', ll_math.FREXP_RESULT)
    yield ('RPyMODF_RESULT', ll_math.MODF_RESULT)
    yield ('RPySTAT_RESULT', ll_os.STAT_RESULT)

def predeclare_utility_functions(db, rtyper):
    # Common utility functions
    def RPyString_New(length=lltype.Signed):
        return lltype.malloc(STR, length)

    for fname, f in locals().items():
        if isinstance(f, types.FunctionType):
            # hack: the defaults give the type of the arguments
            fptr = rtyper.annotate_helper(f, f.func_defaults)
            yield (fname, fptr)

def predeclare_extfunc_helpers(db, rtyper):
    def annotate(func, *argtypes):
        fptr = rtyper.annotate_helper(func, argtypes)
        return (func.__name__, fptr)

    yield annotate(ll_math.ll_frexp_result, lltype.Float, lltype.Signed)
    yield annotate(ll_math.ll_modf_result, lltype.Float, lltype.Float)
    yield annotate(ll_os.ll_stat_result, *([lltype.Signed] * 10))

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
               predeclare_extfunc_helpers,
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
