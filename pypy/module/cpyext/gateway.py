from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.module.cpyext.api import (
    ApiFunction, FUNCTION_declare, INTERPLEVEL_declare, PyObject)
from pypy.module.cpyext.state import State
from pypy.rlib.unroll import unrolling_iterable
import sys
import py

# The same function can be called in three different contexts:
# (1) from C code
# (2) in the test suite, though the "api" object
# (3) from RPython code, for example in the implementation of another function.
#
# In contexts (2) and (3), a function declaring a PyObject argument type will
# receive a wrapped pypy object if the parameter name starts with 'w_', a
# reference (= rffi pointer) otherwise; conversion is automatic.  Context (2)
# only allows calls with a wrapped object.
#
# Functions with a PyObject return type should return a wrapped object.
#
# Functions may raise exceptions.  In context (3), the exception flows normally
# through the calling function.  In context (1) and (2), the exception is
# caught; if it is an OperationError, it is stored in the thread state; other
# exceptions generate a OperationError(w_SystemError); and the funtion returns
# the error value specifed in the API.
#

DEBUG_WRAPPER = True

_NOT_SPECIFIED = object()
CANNOT_FAIL = object()

pypy_debug_catch_fatal_exception = rffi.llexternal('pypy_debug_catch_fatal_exception', [], lltype.Void)

@specialize.memo()
def is_PyObject(TYPE):
    if not isinstance(TYPE, lltype.Ptr):
        return False
    return hasattr(TYPE.TO, 'c_ob_refcnt') and hasattr(TYPE.TO, 'c_ob_type')

def cpython_api(argtypes, restype, error=_NOT_SPECIFIED, external=True):
    """
    Declares a function to be exported.
    - `argtypes`, `restype` are lltypes and describe the function signature.
    - `error` is the value returned when an applevel exception is raised. The
      special value 'CANNOT_FAIL' (also when restype is Void) turns an eventual
      exception into a wrapped SystemError.  Unwrapped exceptions also cause a
      SytemError.
    - set `external` to False to get a C function pointer, but not exported by
      the API headers.
    """
    if error is _NOT_SPECIFIED:
        if restype is PyObject:
            error = lltype.nullptr(restype.TO)
        elif restype is lltype.Void:
            error = CANNOT_FAIL
    if type(error) is int:
        error = rffi.cast(restype, error)

    def decorate(func):
        func_name = func.func_name
        if external:
            c_name = None
        else:
            c_name = func_name
        api_function = ApiFunction(argtypes, restype, func, error, c_name=c_name)
        func.api_func = api_function

        if error is _NOT_SPECIFIED:
            raise ValueError("function %s has no return value for exceptions"
                             % func)
        def make_unwrapper(catch_exception):
            names = api_function.argnames
            types_names_enum_ui = unrolling_iterable(enumerate(
                zip(api_function.argtypes,
                    [tp_name.startswith("w_") for tp_name in names])))

            @specialize.ll()
            def unwrapper(space, *args):
                from pypy.module.cpyext.pyobject import Py_DecRef
                from pypy.module.cpyext.pyobject import make_ref, from_ref
                from pypy.module.cpyext.pyobject import BorrowPair
                newargs = ()
                to_decref = []
                assert len(args) == len(api_function.argtypes)
                for i, (ARG, is_wrapped) in types_names_enum_ui:
                    input_arg = args[i]
                    if is_PyObject(ARG) and not is_wrapped:
                        # build a reference
                        if input_arg is None:
                            arg = lltype.nullptr(PyObject.TO)
                        elif isinstance(input_arg, W_Root):
                            ref = make_ref(space, input_arg)
                            to_decref.append(ref)
                            arg = rffi.cast(ARG, ref)
                        else:
                            arg = input_arg
                    elif is_PyObject(ARG) and is_wrapped:
                        # convert to a wrapped object
                        if input_arg is None:
                            arg = input_arg
                        elif isinstance(input_arg, W_Root):
                            arg = input_arg
                        else:
                            arg = from_ref(space,
                                           rffi.cast(PyObject, input_arg))
                    else:
                        arg = input_arg
                    newargs += (arg, )
                try:
                    try:
                        res = func(space, *newargs)
                    except OperationError, e:
                        if not catch_exception:
                            raise
                        state = space.fromcache(State)
                        state.set_exception(e)
                        if is_PyObject(restype):
                            return None
                        else:
                            if api_function.error_value is _NOT_SPECIFIED:
                                raise
                            return api_function.error_value
                    if res is None:
                        return None
                    elif isinstance(res, BorrowPair):
                        return res.w_borrowed
                    else:
                        return res
                finally:
                    for arg in to_decref:
                        Py_DecRef(space, arg)
            unwrapper.func = func
            unwrapper.api_func = api_function
            unwrapper._always_inline_ = True
            return unwrapper

        unwrapper_catch = make_unwrapper(True)
        unwrapper_raise = make_unwrapper(False)
        if external:
            FUNCTION_declare(func_name, api_function)
        INTERPLEVEL_declare(func_name, unwrapper_catch) # used in tests
        return unwrapper_raise # used in 'normal' RPython code.
    return decorate

# Make the wrapper for the cases (1) and (2)
def make_wrapper(space, callable):
    "NOT_RPYTHON"
    names = callable.api_func.argnames
    argtypes_enum_ui = unrolling_iterable(enumerate(zip(callable.api_func.argtypes,
        [name.startswith("w_") for name in names])))
    fatal_value = callable.api_func.restype._defl()

    @specialize.ll()
    def wrapper(*args):
        from pypy.module.cpyext.pyobject import make_ref, from_ref
        from pypy.module.cpyext.pyobject import BorrowPair
        # we hope that malloc removal removes the newtuple() that is
        # inserted exactly here by the varargs specializer
        llop.gc_stack_bottom(lltype.Void)   # marker for trackgcroot.py
        rffi.stackcounter.stacks_counter += 1
        retval = fatal_value
        boxed_args = ()
        try:
            if not we_are_translated() and DEBUG_WRAPPER:
                print >>sys.stderr, callable,
            assert len(args) == len(callable.api_func.argtypes)
            for i, (typ, is_wrapped) in argtypes_enum_ui:
                arg = args[i]
                if is_PyObject(typ) and is_wrapped:
                    if arg:
                        arg_conv = from_ref(space, rffi.cast(PyObject, arg))
                    else:
                        arg_conv = None
                else:
                    arg_conv = arg
                boxed_args += (arg_conv, )
            state = space.fromcache(State)
            try:
                result = callable(space, *boxed_args)
                if not we_are_translated() and DEBUG_WRAPPER:
                    print >>sys.stderr, " DONE"
            except OperationError, e:
                failed = True
                state.set_exception(e)
            except BaseException, e:
                failed = True
                if not we_are_translated():
                    message = repr(e)
                    import traceback
                    traceback.print_exc()
                else:
                    message = str(e)
                state.set_exception(OperationError(space.w_SystemError,
                                                   space.wrap(message)))
            else:
                failed = False

            if failed:
                error_value = callable.api_func.error_value
                if error_value is CANNOT_FAIL:
                    raise SystemError("The function '%s' was not supposed to fail"
                                      % (callable.__name__,))
                retval = error_value

            elif is_PyObject(callable.api_func.restype):
                if result is None:
                    retval = make_ref(space, None)
                elif isinstance(result, BorrowPair):
                    retval = result.get_ref(space)
                elif not rffi._isllptr(result):
                    retval = rffi.cast(callable.api_func.restype,
                                       make_ref(space, result))
                else:
                    retval = result
            elif callable.api_func.restype is not lltype.Void:
                retval = rffi.cast(callable.api_func.restype, result)
        except Exception, e:
            if not we_are_translated():
                import traceback
                traceback.print_exc()
                print str(e)
                # we can't do much here, since we're in ctypes, swallow
            else:
                print str(e)
                pypy_debug_catch_fatal_exception()
        rffi.stackcounter.stacks_counter -= 1
        return retval
    callable._always_inline_ = True
    wrapper.__name__ = "wrapper for %r" % (callable, )
    return wrapper

@specialize.ll()
def generic_cpy_call(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, True, False)(space, func, *args)

@specialize.ll()
def generic_cpy_call_dont_decref(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, False, False)(space, func, *args)

@specialize.ll()    
def generic_cpy_call_expect_null(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, True, True)(space, func, *args)

@specialize.memo()
def make_generic_cpy_call(FT, decref_args, expect_null):
    from pypy.module.cpyext.pyobject import make_ref, from_ref, Py_DecRef
    from pypy.module.cpyext.pyobject import RefcountState
    from pypy.module.cpyext.pyerrors import PyErr_Occurred
    unrolling_arg_types = unrolling_iterable(enumerate(FT.ARGS))
    RESULT_TYPE = FT.RESULT

    # copied and modified from rffi.py
    # We need tons of care to ensure that no GC operation and no
    # exception checking occurs in call_external_function.
    argnames = ', '.join(['a%d' % i for i in range(len(FT.ARGS))])
    source = py.code.Source("""
        def call_cpyext_external_function(funcptr, %(argnames)s):
            # NB. it is essential that no exception checking occurs here!
            res = funcptr(%(argnames)s)
            return res
    """ % locals())
    miniglobals = {'__name__':    __name__, # for module name propagation
                   }
    exec source.compile() in miniglobals
    call_external_function = miniglobals['call_cpyext_external_function']
    call_external_function._dont_inline_ = True
    call_external_function._annspecialcase_ = 'specialize:ll'
    call_external_function._gctransformer_hint_close_stack_ = True
    # don't inline, as a hack to guarantee that no GC pointer is alive
    # anywhere in call_external_function

    @specialize.ll()
    def generic_cpy_call(space, func, *args):
        boxed_args = ()
        to_decref = []
        assert len(args) == len(FT.ARGS)
        for i, ARG in unrolling_arg_types:
            arg = args[i]
            if is_PyObject(ARG):
                if arg is None:
                    boxed_args += (lltype.nullptr(PyObject.TO),)
                elif isinstance(arg, W_Root):
                    ref = make_ref(space, arg)
                    boxed_args += (ref,)
                    if decref_args:
                        to_decref.append(ref)
                else:
                    boxed_args += (arg,)
            else:
                boxed_args += (arg,)

        try:
            # create a new container for borrowed references
            state = space.fromcache(RefcountState)
            old_container = state.swap_borrow_container(None)
            try:
                # Call the function
                result = call_external_function(func, *boxed_args)
            finally:
                state.swap_borrow_container(old_container)

            if is_PyObject(RESULT_TYPE):
                if result is None:
                    ret = result
                elif isinstance(result, W_Root):
                    ret = result
                else:
                    ret = from_ref(space, result)
                    # The object reference returned from a C function
                    # that is called from Python must be an owned reference
                    # - ownership is transferred from the function to its caller.
                    if result:
                        Py_DecRef(space, result)

                # Check for exception consistency
                has_error = PyErr_Occurred(space) is not None
                has_result = ret is not None
                if has_error and has_result:
                    raise OperationError(space.w_SystemError, space.wrap(
                        "An exception was set, but function returned a value"))
                elif not expect_null and not has_error and not has_result:
                    raise OperationError(space.w_SystemError, space.wrap(
                        "Function returned a NULL result without setting an exception"))

                if has_error:
                    state = space.fromcache(State)
                    state.check_and_raise_exception()

                return ret
            return result
        finally:
            if decref_args:
                for ref in to_decref:
                    Py_DecRef(space, ref)
    return generic_cpy_call
