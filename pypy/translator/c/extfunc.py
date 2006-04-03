import types
from pypy.objspace.flow.model import FunctionGraph
from pypy.rpython.lltypesystem import lltype
from pypy.translator.c.support import cdecl
from pypy.rpython.rstr import STR
from pypy.rpython import rstr
from pypy.rpython.lltypesystem import rlist
from pypy.rpython.module import ll_os, ll_time, ll_math, ll_strtod
from pypy.rpython.module import ll_stackless, ll_stack
from pypy.module.thread.rpython import ll_thread
from pypy.module._socket.rpython import ll__socket

# table of functions hand-written in src/ll_*.h
EXTERNALS = {
    ll_os  .ll_os_open:    'LL_os_open',
    ll_os  .ll_read_into:  'LL_read_into',
    ll_os  .ll_os_write:   'LL_os_write',
    ll_os  .ll_os_close:   'LL_os_close',
    ll_os  .ll_os_dup:     'LL_os_dup',
    ll_os  .ll_os_stat:    'LL_os_stat',
    ll_os  .ll_os_fstat:   'LL_os_fstat',
    ll_os  .ll_os_lseek:   'LL_os_lseek',
    ll_os  .ll_os_isatty:  'LL_os_isatty',
    ll_os  .ll_os_ftruncate:'LL_os_ftruncate',
    ll_os  .ll_os_strerror: 'LL_os_strerror',
    ll_os  .ll_os_system:  'LL_os_system',
    ll_os  .ll_os_unlink:  'LL_os_unlink',
    ll_os  .ll_os_getcwd:  'LL_os_getcwd',
    ll_os  .ll_os_chdir:   'LL_os_chdir',
    ll_os  .ll_os_mkdir:   'LL_os_mkdir',
    ll_os  .ll_os_rmdir:   'LL_os_rmdir',
    ll_os  .ll_os_putenv:  'LL_os_putenv',
    ll_os  .ll_os_unsetenv:'LL_os_unsetenv',
    ll_os  .ll_os_environ: 'LL_os_environ',
    ll_os  .ll_os_opendir: 'LL_os_opendir',
    ll_os  .ll_os_readdir: 'LL_os_readdir',
    ll_os  .ll_os_closedir:'LL_os_closedir',
    ll_time.ll_time_clock: 'LL_time_clock',
    ll_time.ll_time_sleep: 'LL_time_sleep',
    ll_time.ll_time_time:  'LL_time_time',
    ll_math.ll_math_pow:   'LL_math_pow',
    ll_math.ll_math_frexp: 'LL_math_frexp',
    ll_math.ll_math_atan2: 'LL_math_atan2',
    ll_math.ll_math_fmod : 'LL_math_fmod',
    ll_math.ll_math_ldexp: 'LL_math_ldexp',
    ll_math.ll_math_modf:  'LL_math_modf',
    ll_math.ll_math_hypot: 'LL_math_hypot',
    ll_strtod.ll_strtod_parts_to_float:
        'LL_strtod_parts_to_float',
    ll_strtod.ll_strtod_formatd:
        'LL_strtod_formatd',
    ll_thread.ll_newlock:            'LL_thread_newlock',
    ll_thread.ll_acquirelock:        'LL_thread_acquirelock',
    ll_thread.ll_releaselock:        'LL_thread_releaselock',
    ll_thread.ll_fused_releaseacquirelock: 'LL_thread_fused_releaseacquirelock',
    ll_thread.ll_thread_start:     'LL_thread_start',
    ll_thread.ll_thread_get_ident: 'LL_thread_get_ident',
    ll_stackless.ll_stackless_switch:             'LL_stackless_switch',
    ll_stackless.ll_stackless_stack_frames_depth: 'LL_stackless_stack_frames_depth',
    ll_stack.ll_stack_unwind: 'LL_stack_unwind',
    ll_stack.ll_stack_too_big: 'LL_stack_too_big',
    ll__socket.ll__socket_gethostname:   'LL__socket_gethostname',
    ll__socket.ll__socket_gethostbyname: 'LL__socket_gethostbyname',
    ll__socket.ll__socket_getaddrinfo:   'LL__socket_getaddrinfo',
    ll__socket.ll__socket_nextaddrinfo:  'LL__socket_nextaddrinfo',
    ll__socket.ll__socket_freeaddrinfo:  'LL__socket_freeaddrinfo',
    ll__socket.ll__socket_ntohs: 'LL__socket_ntohs',
    ll__socket.ll__socket_htons: 'LL__socket_htons',
    ll__socket.ll__socket_htonl: 'LL__socket_htonl',
    ll__socket.ll__socket_ntohl: 'LL__socket_htonl',
    ll__socket.ll__socket_newsocket: 'LL__socket_newsocket',
    ll__socket.ll__socket_connect: 'LL__socket_connect',
    ll__socket.ll__socket_getpeername: 'LL__socket_getpeername',
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

def find_list_of_str(rtyper):
    for r in rtyper.reprs.itervalues():
        if isinstance(r, rlist.ListRepr) and r.item_repr is rstr.string_repr:
            return r.lowleveltype.TO
    return None

def predeclare_common_types(db, rtyper, optimize=True):
    # Common types
    yield ('RPyString', STR)
    LIST_OF_STR = find_list_of_str(rtyper)
    if LIST_OF_STR is not None:
        yield ('RPyListOfString', LIST_OF_STR)
    yield ('RPyFREXP_RESULT', ll_math.FREXP_RESULT)
    yield ('RPyMODF_RESULT', ll_math.MODF_RESULT)
    yield ('RPySTAT_RESULT', ll_os.STAT_RESULT)
    yield ('RPySOCKET_ADDRINFO', ll__socket.ADDRINFO_RESULT)
    yield ('RPySOCKET_SOCKNAME', ll__socket.SOCKNAME)

def predeclare_utility_functions(db, rtyper, optimize=True):
    # Common utility functions
    def RPyString_New(length=lltype.Signed):
        return lltype.malloc(STR, length)

    # !!!
    # be extremely careful passing a gc tracked object
    # from such an helper result to another one
    # as argument, this could result in leaks
    # Such result should be only from C code
    # returned directly as results

    LIST_OF_STR = find_list_of_str(rtyper)
    if LIST_OF_STR is not None:
        p = lltype.Ptr(LIST_OF_STR)

        def _RPyListOfString_New(length=lltype.Signed):
            return LIST_OF_STR.ll_newlist(length)

        def _RPyListOfString_SetItem(l=p,
                                    index=lltype.Signed,
                                    newstring=lltype.Ptr(STR)):
            rlist.ll_setitem_nonneg(rlist.dum_nocheck, l, index, newstring)

    for fname, f in locals().items():
        if isinstance(f, types.FunctionType):
            # XXX this is painful :(
            if (LIST_OF_STR, fname) in db.helper2ptr:
                yield (fname, db.helper2ptr[LIST_OF_STR, fname])
            else:
                # hack: the defaults give the type of the arguments
                graph = rtyper.annotate_helper(f, f.func_defaults)
                db.helper2ptr[LIST_OF_STR, fname] = graph
                yield (fname, graph)


def get_extfunc_helper_ptrs(db, rtyper, optimize=True):
    # XXX need some way of finding out if the externals needing have
    # been annotated -- db.externalfuncs gets filled out by
    # select_function_code_generator which is called from
    # FuncNode.__init__ (probably...) which is after this gets called.
    optimize = False 
    def annotate(func, *argtypes):
        fptr = rtyper.annotate_helper(func, argtypes)
        db.helper2ptr[func] = fptr
        return (func.__name__, fptr)

    r = []

    if ll_math.ll_math_frexp in db.externalfuncs or not optimize:
        r.append(annotate(ll_math.ll_frexp_result, lltype.Float, lltype.Signed))
        
    if ll_math.ll_math_modf in db.externalfuncs or not optimize:
        r.append(annotate(ll_math.ll_modf_result, lltype.Float, lltype.Float))

    if (ll_os.ll_os_stat in db.externalfuncs or
        ll_os.ll_os_fstat in db.externalfuncs or
        not optimize):
        r.append(annotate(ll_os.ll_stat_result, *([lltype.Signed] * 10)))

    if (ll__socket.ll__socket_nextaddrinfo in db.externalfuncs or
        not optimize):
        args = [lltype.Signed, lltype.Signed, lltype.Signed, lltype.Ptr(STR),
                lltype.Ptr(STR), lltype.Signed, lltype.Signed, lltype.Signed]
        r.append(annotate(ll__socket.ll__socket_addrinfo, *args))
        
    if (ll__socket.ll__socket_getpeername in db.externalfuncs or
        not optimize):
        args = [lltype.Ptr(STR), lltype.Signed, lltype.Signed, lltype.Signed]
        r.append(annotate(ll__socket.ll__socket_sockname, *args))

    return r

def predeclare_extfunc_helpers(db, rtyper, optimize=True):
    def decl(f):
        return (f.__name__, db.helper2ptr[f])
    
    if ll_math.ll_math_frexp in db.externalfuncs or not optimize:
        yield decl(ll_math.ll_frexp_result)
        yield ('LL_NEED_MATH_FREXP', 1)
        
    if ll_math.ll_math_modf in db.externalfuncs or not optimize:
        yield decl(ll_math.ll_modf_result)
        yield ('LL_NEED_MATH_MODF', 1)

    if (ll_os.ll_os_stat in db.externalfuncs or
        ll_os.ll_os_fstat in db.externalfuncs or
        not optimize):
        yield decl(ll_os.ll_stat_result)
        yield ('LL_NEED_OS_STAT', 1)

    if (ll__socket.ll__socket_nextaddrinfo in db.externalfuncs or
        not optimize):
        yield decl(ll__socket.ll__socket_addrinfo)
        yield ('LL_NEED__SOCKET_ADDRINFO', 1)
        
    if (ll__socket.ll__socket_getpeername in db.externalfuncs or
        not optimize):
        yield decl(ll__socket.ll__socket_sockname)
        yield ('LL_NEED__SOCKET_SOCKNAME', 1)

def predeclare_extfuncs(db, rtyper, optimize=True):
    modules = {}
    def module_name(c_name):
        frags = c_name[3:].split('_')
        if frags[0] == '':
            return '_' + frags[1]
        else:
            return frags[0]

    for func, funcobj in db.externalfuncs.items():
        c_name = EXTERNALS[func]
        # construct a define LL_NEED_<modname> to make it possible to isolate in-develpoment externals and headers
        modname = module_name(c_name)
        if modname not in modules:
            modules[modname] = True
            yield 'LL_NEED_%s' % modname.upper(), 1
        funcptr = lltype._ptr(lltype.Ptr(lltype.typeOf(funcobj)), funcobj) # hum
        yield c_name, funcptr

def predeclare_exception_data(db, rtyper, optimize=True):
    # Exception-related types and constants
    exceptiondata = rtyper.getexceptiondata()

    yield ('RPYTHON_EXCEPTION_VTABLE', exceptiondata.lltype_of_exception_type)
    yield ('RPYTHON_EXCEPTION',        exceptiondata.lltype_of_exception_value)

    yield ('RPYTHON_EXCEPTION_MATCH',  exceptiondata.fn_exception_match)
    yield ('RPYTHON_TYPE_OF_EXC_INST', exceptiondata.fn_type_of_exc_inst)
    yield ('RPYTHON_RAISE_OSERROR',    exceptiondata.fn_raise_OSError)
    if not db.standalone:
        yield ('RPYTHON_PYEXCCLASS2EXC', exceptiondata.fn_pyexcclass2exc)

    for pyexccls in exceptiondata.standardexceptions:
        exc_llvalue = exceptiondata.fn_pyexcclass2exc(
            lltype.pyobjectptr(pyexccls))
        # strange naming here because the macro name must be
        # a substring of PyExc_%s
        name = pyexccls.__name__
        if pyexccls.__module__ != 'exceptions':
            name = '%s_%s' % (pyexccls.__module__.replace('.', '__'), name)
        yield ('RPyExc_%s' % name, exc_llvalue)


def predeclare_all(db, rtyper, optimize=True):
    for fn in [predeclare_common_types,
               predeclare_utility_functions,
               predeclare_exception_data,
               predeclare_extfunc_helpers,
               predeclare_extfuncs,
               ]:
        for t in fn(db, rtyper, optimize):
            yield t


def get_all(db, rtyper, optimize=True):
    for fn in [predeclare_common_types,
               predeclare_utility_functions,
               predeclare_exception_data,
               get_extfunc_helper_ptrs,
               predeclare_extfuncs,
               ]:
        for t in fn(db, rtyper, optimize):
            yield t[1]

# ____________________________________________________________

def do_the_getting(db, rtyper):

    decls = list(get_all(db, rtyper))
    rtyper.specialize_more_blocks()

    for obj in decls:
        if isinstance(obj, lltype.LowLevelType):
            db.gettype(obj)
        elif isinstance(obj, FunctionGraph):
            db.get(rtyper.getcallable(obj))
        else:
            db.get(obj)


def pre_include_code_lines(db, rtyper):
    # generate some #defines that go before the #include to provide
    # predeclared well-known names for constant objects, functions and
    # types.  These names are then used by the #included files, like
    # g_exception.h.

    def predeclare(c_name, lowlevelobj):
        llname = db.get(lowlevelobj)
        assert '\n' not in llname
        return '#define\t%s\t%s' % (c_name, llname)

    def predeclaretype(c_typename, lowleveltype):
        typename = db.gettype(lowleveltype)
        return 'typedef %s;' % cdecl(typename, c_typename)

    yield '#define HAVE_RTYPER'
    decls = list(predeclare_all(db, rtyper))

    for c_name, obj in decls:
        if isinstance(obj, lltype.LowLevelType):
            yield predeclaretype(c_name, obj)
        elif isinstance(obj, FunctionGraph):
            yield predeclare(c_name, rtyper.getcallable(obj))
        else:
            yield predeclare(c_name, obj)
