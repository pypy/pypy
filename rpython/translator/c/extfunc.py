import types

from rpython.flowspace.model import FunctionGraph
from rpython.rtyper.lltypesystem import lltype, rstr, rlist
from rpython.rtyper.lltypesystem.rstr import STR, mallocstr
from rpython.translator.c.support import cdecl


def find_list_of_str(rtyper):
    for r in rtyper.reprs.itervalues():
        if isinstance(r, rlist.ListRepr) and r.item_repr is rstr.string_repr:
            return r.lowleveltype.TO
    return None

def predeclare_common_types(db, rtyper):
    # Common types
    yield ('RPyString', STR)
    LIST_OF_STR = find_list_of_str(rtyper)
    if LIST_OF_STR is not None:
        yield ('RPyListOfString', LIST_OF_STR)

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


def predeclare_extfuncs(db, rtyper):
    modules = {}
    def module_name(c_name):
        frags = c_name[3:].split('_')
        if frags[0] == '':
            return '_' + frags[1]
        else:
            return frags[0]

    for func, funcobj in db.externalfuncs.items():
        # construct a define LL_NEED_<modname> to make it possible to isolate in-development externals and headers
        modname = module_name(func)
        if modname not in modules:
            modules[modname] = True
            yield 'LL_NEED_%s' % modname.upper(), 1
        funcptr = funcobj._as_ptr()
        yield func, funcptr

def predeclare_exception_data(db, rtyper):
    # Exception-related types and constants
    exceptiondata = rtyper.exceptiondata
    exctransformer = db.exctransformer

    yield ('RPYTHON_EXCEPTION_VTABLE', exceptiondata.lltype_of_exception_type)
    yield ('RPYTHON_EXCEPTION',        exceptiondata.lltype_of_exception_value)

    yield ('RPYTHON_EXCEPTION_MATCH',  exceptiondata.fn_exception_match)
    yield ('RPYTHON_TYPE_OF_EXC_INST', exceptiondata.fn_type_of_exc_inst)
    yield ('RPYTHON_RAISE_OSERROR',    exceptiondata.fn_raise_OSError)

    yield ('RPyExceptionOccurred1',    exctransformer.rpyexc_occured_ptr.value)
    yield ('RPyFetchExceptionType',    exctransformer.rpyexc_fetch_type_ptr.value)
    yield ('RPyFetchExceptionValue',   exctransformer.rpyexc_fetch_value_ptr.value)
    yield ('RPyClearException',        exctransformer.rpyexc_clear_ptr.value)
    yield ('RPyRaiseException',        exctransformer.rpyexc_raise_ptr.value)

    for exccls in exceptiondata.standardexceptions:
        exc_llvalue = exceptiondata.get_standard_ll_exc_instance_by_class(
            exccls)
        # strange naming here because the macro name must be
        # a substring of PyExc_%s
        name = exccls.__name__
        if exccls.__module__ != 'exceptions':
            name = '%s_%s' % (exccls.__module__.replace('.', '__'), name)
        yield ('RPyExc_%s' % name, exc_llvalue)


def predeclare_all(db, rtyper):
    for fn in [predeclare_common_types,
               predeclare_utility_functions,
               predeclare_exception_data,
               predeclare_extfuncs,
               ]:
        for t in fn(db, rtyper):
            yield t


def get_all(db, rtyper):
    for fn in [predeclare_common_types,
               predeclare_utility_functions,
               predeclare_exception_data,
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
