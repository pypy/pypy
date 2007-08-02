import types
from pypy.objspace.flow.model import FunctionGraph
from pypy.rpython.lltypesystem import lltype
from pypy.translator.c.support import cdecl
from pypy.rpython.lltypesystem.rstr import STR, mallocstr
from pypy.rpython.lltypesystem import rstr
from pypy.rpython.lltypesystem import rlist
from pypy.rpython.module import ll_time, ll_os
from pypy.rpython.module import ll_stackless, ll_stack
from pypy.rpython.lltypesystem.module.ll_os import STAT_RESULT, PIPE_RESULT
from pypy.rpython.lltypesystem.module.ll_os import WAITPID_RESULT
from pypy.rpython.lltypesystem.module.ll_os import Implementation as impl
from pypy.rpython.lltypesystem.module import ll_strtod
from pypy.rlib import ros

try:
    from pypy.module.thread.rpython import ll_thread
except ImportError:
    ll_thread = None

# table of functions hand-written in src/ll_*.h
# Note about *.im_func: The annotator and the rtyper expect direct
# references to functions, so we cannot insert classmethods here.

EXTERNALS = {
    impl.ll_os_stat.im_func:    'LL_os_stat',
    impl.ll_os_fstat.im_func:   'LL_os_fstat',
    impl.ll_os_lstat.im_func:   'LL_os_lstat',
    impl.ll_os_lseek.im_func:   'LL_os_lseek',
    impl.ll_os_isatty.im_func:  'LL_os_isatty',
    impl.ll_os_ftruncate.im_func:'LL_os_ftruncate',
    impl.ll_os_strerror.im_func: 'LL_os_strerror',
    impl.ll_os_system.im_func:  'LL_os_system',
    impl.ll_os_unlink.im_func:  'LL_os_unlink',
    impl.ll_os_getcwd.im_func:  'LL_os_getcwd',
    impl.ll_os_chdir.im_func:   'LL_os_chdir',
    impl.ll_os_mkdir.im_func:   'LL_os_mkdir',
    impl.ll_os_rmdir.im_func:   'LL_os_rmdir',
    impl.ll_os_putenv.im_func:  'LL_os_putenv',
    impl.ll_os_unsetenv.im_func:'LL_os_unsetenv',
    impl.ll_os_environ.im_func: 'LL_os_environ',
    impl.ll_os_opendir.im_func: 'LL_os_opendir',
    impl.ll_os_readdir.im_func: 'LL_os_readdir',
    impl.ll_os_closedir.im_func:'LL_os_closedir',
    impl.ll_os_pipe.im_func:    'LL_os_pipe',
    impl.ll_os_chmod.im_func:   'LL_os_chmod',
    impl.ll_os_rename.im_func:  'LL_os_rename',
    impl.ll_os_umask.im_func:   'LL_os_umask',
    impl.ll_os_getpid.im_func:  'LL_os_getpid',
    impl.ll_os_kill.im_func:    'LL_os_kill',
    impl.ll_os_link.im_func:    'LL_os_link',
    impl.ll_os_symlink.im_func: 'LL_os_symlink',
    impl.ll_readlink_into:      'LL_readlink_into',
    impl.ll_os_fork.im_func:    'LL_os_fork',
    impl.ll_os_spawnv.im_func:  'LL_os_spawnv',
    impl.ll_os_waitpid.im_func: 'LL_os_waitpid',
    impl.ll_os__exit.im_func:   'LL_os__exit',
    ll_time.ll_time_clock: 'LL_time_clock',
    ll_time.ll_time_sleep: 'LL_time_sleep',
    ll_time.ll_time_time:  'LL_time_time',
    ll_strtod.Implementation.ll_strtod_parts_to_float:
        'LL_strtod_parts_to_float',
    ll_strtod.Implementation.ll_strtod_formatd:
        'LL_strtod_formatd',
    ll_stackless.ll_stackless_switch:             'LL_stackless_switch',
    ll_stackless.ll_stackless_stack_frames_depth: 'LL_stackless_stack_frames_depth',
    ll_stack.ll_stack_unwind: 'LL_stack_unwind',
    ll_stack.ll_stack_too_big: 'LL_stack_too_big',
    }

if ll_thread: EXTERNALS.update({
    ll_thread.ll_newlock:            'LL_thread_newlock',
    ll_thread.ll_acquirelock:        'LL_thread_acquirelock',
    ll_thread.ll_releaselock:        'LL_thread_releaselock',
    ll_thread.ll_fused_releaseacquirelock: 'LL_thread_fused_releaseacquirelock',
    ll_thread.ll_thread_start:     'LL_thread_start',
    ll_thread.ll_thread_get_ident: 'LL_thread_get_ident',
    })

#______________________________________________________
# insert 'simple' math functions into EXTERNALs table:

# XXX: messy, messy, messy
# this interacts in strange ways with node.select_function_code_generators,
# because it fakes to be an ll_* function.

math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh',
    'frexp', 'pow', 'atan2', 'fmod', 'ldexp', 'modf', 'hypot'
    ]

import math
for name in math_functions:
    EXTERNALS['ll_math.ll_math_%s' % name] = 'LL_math_%s' % name

EXTERNALS['LL_flush_icache'] = 'LL_flush_icache'

#______________________________________________________

def find_list_of_str(rtyper):
    for r in rtyper.reprs.itervalues():
        if isinstance(r, rlist.ListRepr) and r.item_repr is rstr.string_repr:
            return r.lowleveltype.TO
    return None

def predeclare_common_types(db, rtyper):
    from pypy.rpython.lltypesystem.module import ll_math
    # Common types
    yield ('RPyString', STR)
    LIST_OF_STR = find_list_of_str(rtyper)
    if LIST_OF_STR is not None:
        yield ('RPyListOfString', LIST_OF_STR)
    yield ('RPyFREXP_RESULT', ll_math.FREXP_RESULT)
    yield ('RPyMODF_RESULT', ll_math.MODF_RESULT)
    yield ('RPySTAT_RESULT', STAT_RESULT)
    yield ('RPyPIPE_RESULT', PIPE_RESULT)
    yield ('RPyWAITPID_RESULT', WAITPID_RESULT)

def predeclare_utility_functions(db, rtyper):
    # Common utility functions
    def RPyString_New(length=lltype.Signed):
        return mallocstr(length)

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

        def _RPyListOfString_New(length=lltype.Signed):
            return LIST_OF_STR.ll_newlist(length)

        def _RPyListOfString_SetItem(l=p,
                                    index=lltype.Signed,
                                    newstring=lltype.Ptr(STR)):
            rlist.ll_setitem_nonneg(rlist.dum_nocheck, l, index, newstring)

        def _RPyListOfString_GetItem(l=p,
                                    index=lltype.Signed):
            return rlist.ll_getitem_fast(l, index)

        def _RPyListOfString_Length(l=p):
            return rlist.ll_length(l)

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


def get_extfunc_helper_ptrs(db, rtyper):

    def annotate(func, args):
        fptr = rtyper.annotate_helper(func, args)
        db.helper2ptr[func] = fptr
        return (func.__name__, fptr)

    for func, args, symb in db.translator._implicitly_called_by_externals:
        yield annotate(func, args)

def predeclare_extfunc_helpers(db, rtyper):
    def decl(func):
        return (func.__name__, db.helper2ptr[func])

    for func, args, symb in db.translator._implicitly_called_by_externals:
        yield decl(func)
        yield ('LL_NEED_' + symb, 1)

def predeclare_extfuncs(db, rtyper):
    modules = {}
    def module_name(c_name):
        frags = c_name[3:].split('_')
        if frags[0] == '':
            return '_' + frags[1]
        else:
            return frags[0]

    for func, funcobj in db.externalfuncs.items():
        c_name = EXTERNALS[func]
        # construct a define LL_NEED_<modname> to make it possible to isolate in-development externals and headers
        modname = module_name(c_name)
        if modname not in modules:
            modules[modname] = True
            yield 'LL_NEED_%s' % modname.upper(), 1
        funcptr = funcobj._as_ptr()
        yield c_name, funcptr

def predeclare_exception_data(db, rtyper):
    # Exception-related types and constants
    exceptiondata = rtyper.getexceptiondata()
    exctransformer = db.exctransformer

    yield ('RPYTHON_EXCEPTION_VTABLE', exceptiondata.lltype_of_exception_type)
    yield ('RPYTHON_EXCEPTION',        exceptiondata.lltype_of_exception_value)

    yield ('RPYTHON_EXCEPTION_MATCH',  exceptiondata.fn_exception_match)
    yield ('RPYTHON_TYPE_OF_EXC_INST', exceptiondata.fn_type_of_exc_inst)
    yield ('RPYTHON_RAISE_OSERROR',    exceptiondata.fn_raise_OSError)
    if not db.standalone:
        yield ('RPYTHON_PYEXCCLASS2EXC', exceptiondata.fn_pyexcclass2exc)

    yield ('_RPyExceptionOccurred',    exctransformer._rpyexc_occured_ptr.value)
    yield ('RPyExceptionOccurred1',    exctransformer.rpyexc_occured_ptr.value)
    yield ('RPyFetchExceptionType',    exctransformer.rpyexc_fetch_type_ptr.value)
    yield ('RPyFetchExceptionValue',   exctransformer.rpyexc_fetch_value_ptr.value)
    yield ('RPyClearException',        exctransformer.rpyexc_clear_ptr.value)
    yield ('RPyRaiseException',        exctransformer.rpyexc_raise_ptr.value)

    for pyexccls in exceptiondata.standardexceptions:
        exc_llvalue = exceptiondata.fn_pyexcclass2exc(
            lltype.pyobjectptr(pyexccls))
        # strange naming here because the macro name must be
        # a substring of PyExc_%s
        name = pyexccls.__name__
        if pyexccls.__module__ != 'exceptions':
            name = '%s_%s' % (pyexccls.__module__.replace('.', '__'), name)
        yield ('RPyExc_%s' % name, exc_llvalue)


def predeclare_all(db, rtyper):
    for fn in [predeclare_common_types,
               predeclare_utility_functions,
               predeclare_exception_data,
               predeclare_extfunc_helpers,
               predeclare_extfuncs,
               ]:
        for t in fn(db, rtyper):
            yield t


def get_all(db, rtyper):
    for fn in [predeclare_common_types,
               predeclare_utility_functions,
               predeclare_exception_data,
               get_extfunc_helper_ptrs,
               predeclare_extfuncs,
               ]:
        for t in fn(db, rtyper):
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
