from pypy.translator.c.extfunc import *

def predeclare_extfunc_helpers(db, rtyper, optimize=True):
    def annotate(func, args):
        fptr = rtyper.annotate_helper(func, args)
        db.helper2ptr[func] = fptr
        return (func.__name__, fptr)

    for func, args, symb in db.translator._implicitly_called_by_externals:
        yield annotate(func, args)
        yield ('LL_NEED_' + symb, 1)

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

