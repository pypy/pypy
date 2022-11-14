import re
from rpython.translator import exceptiontransform
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize
from rpython.rlib.debug import fatalerror_notb
from pypy.interpreter.error import OperationError
from pypy.module._hpy_universal import llapi

def _restore_gil_state(gil_release, _gil_auto):
    from rpython.rlib import rgil
    # see "Handling of the GIL" above
    unlock = gil_release or _gil_auto
    if unlock:
        rgil.release()

def deadlock_error(funcname):
    fatalerror_notb("GIL deadlock detected when a CPython C extension "
                    "module calls '%s'" % (funcname,))

def no_gil_error(funcname):
    fatalerror_notb("GIL not held when a CPython C extension "
                    "module calls '%s'" % (funcname,))


class APISet(object):

    def __init__(self, cts, is_debug, prefix=r'^_?HPy_?', force_c_name=False):
        self.cts = cts
        self.is_debug = is_debug
        self.prefix = re.compile(prefix)
        self.force_c_name = force_c_name
        self.all_functions = []
        self.frozen = False

    def _freeze_(self):
        self.all_functions = unrolling_iterable(self.all_functions)
        self.frozen = True
        return True

    def parse_signature(self, cdecl, error_value):
        d = self.cts.parse_func(cdecl)
        ARGS = d.get_llargs(self.cts)
        RESULT = d.get_llresult(self.cts)
        FUNC = lltype.Ptr(lltype.FuncType(ARGS, RESULT))
        return d.name, FUNC, self.get_ll_errval(d, FUNC, error_value)

    def get_ll_errval(self, d, FUNC, error_value):
        c_result_t = d.tp.result.get_c_name() # a string such as "HPy" or "void"
        if error_value is None:
            # automatically determine the error value from the return type
            if c_result_t == 'HPy':
                return 0
            elif c_result_t == 'void':
                return None
            elif isinstance(FUNC.TO.RESULT, lltype.Ptr):
                return lltype.nullptr(FUNC.TO.RESULT.TO)
            else:
                raise Exception(
                    "API function %s: you must explicitly specify an error_value "
                    "for functions returning %s" % (d.name, c_result_t))
        elif error_value == 'CANNOT_FAIL':
            # we need to specify an error_value anyway, let's just use the
            # exceptiontransform default
            return exceptiontransform.default_error_value(FUNC.TO.RESULT)
        else:
            assert c_result_t != 'HPy' # sanity check
            if lltype.typeOf(error_value) != FUNC.TO.RESULT:
                raise Exception(
                    "API function %s: the specified error_value has the "
                    "wrong lltype: expected %s, got %s" % (d.name, FUNC.TO.RESULT,
                                                           lltype.typeOf(error_value)))
            return error_value


    def func(self, cdecl, cpyext=False, func_name=None, error_value=None,
             is_helper=False, gil=None):
        """
        Declare an HPy API function.

        If the function is marked as cpyext=True, it will be included in the
        translation only if pypy.objspace.hpy_cpyext_API==True (the
        default). This is useful to exclude cpyext in test_ztranslation

        If func_name is given, the decorated function will be automatically
        renamed. Useful for automatically generated code, for example in
        interp_number.py

        error_value specifies the C value to return in case the function
        raises an RPython exception. The default behavior tries to be smart
        enough to work in the most common and standardized cases, but without
        guessing in case of doubts.  In particular, there is no default
        error_value for "int" functions, because CPython's behavior is not
        consistent.

        error_value can be:

            - None (the default): automatically determine the error value. It
              works only for the following return types:
                  * HPy: 0
                  * void: None
                  * pointers: NULL

            - 'CANNOT_FAIL': special string to specify that this function is
              not supposed to fail.

            - a specific value: in this case, the lltype must exactly match
              what is specified for the function type.

        is_helper=True is for functions which are not in the ctx. Useful if
        you need a ll_helper with a specific C signature, for example to use
        as a C callback.

        gil is for handling the PyPy GIL before and after the call. This is
        currently a subset of the cpyext handling, it may expand in the future.

        gil can be:

            - None (the default): the GIL should be held, If not held, acquire
              it before the call and release it after the call. This is useful
              when using HPy in C++/DLL initialization functions before proper
              interpreter startup.
            - "acquire": deadlock if the GIL is not currently held, and acquire
              it before the call. Do nothing after the call (continue holding it).
            - "release": do nothing in the call, release the GIL after the call
        """
        from rpython.rlib import rgil
        if self.frozen:
            raise RuntimeError(
                'Too late to call @api.func(), the API object has already been frozen. '
                'If you are calling @api.func() to decorate module-level functions, '
                'you might solve this by making sure that the module is imported '
                'earlier')
        gil_auto_workaround = (gil is None)  # automatically detect when we don't
                                             # have the GIL, and acquire/release it
        gil_acquire = (gil == "acquire")
        gil_release = (gil == "release")
        assert (gil is None or gil_acquire or gil_release)
        
        def decorate(fn):
            from pypy.module._hpy_universal.state import State
            name, ll_functype, ll_errval = self.parse_signature(cdecl, error_value)
            if name != fn.__name__:
                raise ValueError(
                    'The name of the function and the signature do not match: '
                    '%s != %s' % (name, fn.__name__))
            #
            if func_name is not None:
                fn = func_with_new_name(fn, func_name)
            #
            # attach various helpers to fn, so you can access things like
            # HPyNumber_Add.get_llhelper(), HPyNumber_Add.basename, etc.

            # get_llhelper
            @specialize.memo()
            def make_wrapper(space):
                def wrapper(*args):
                    _gil_auto = False
                    if gil_auto_workaround and not rgil.am_I_holding_the_GIL():
                        _gil_auto = True
                    if _gil_auto or gil_acquire:
                        if gil_acquire and rgil.am_I_holding_the_GIL():
                            deadlock_error(fn.__name__)
                        rgil.acquire()
                    else:
                        if not rgil.am_I_holding_the_GIL():
                            no_gil_error(fn.__name__)
                    state = space.fromcache(State)
                    handles = state.get_handle_manager(self.is_debug)
                    try:
                        retval = fn(space, handles, *args)
                    except OperationError as e:
                        _restore_gil_state(gil_release, _gil_auto)
                        state.set_exception(e)
                        return ll_errval
                    _restore_gil_state(gil_release, _gil_auto)
                    return retval
                wrapper.__name__ = 'ctx_%s' % fn.__name__
                if self.force_c_name:
                    wrapper.c_name = fn.__name__
                return wrapper
            def get_llhelper(space):
                return llhelper(ll_functype, make_wrapper(space))
            get_llhelper.__name__ = 'get_llhelper_%s' % fn.__name__
            fn.get_llhelper = get_llhelper

            # basename
            fn.basename = self.prefix.sub(r'', fn.__name__)

            fn.cpyext = cpyext
            fn.is_helper = is_helper
            # record it into the API
            self.all_functions.append(fn)
            return fn
        return decorate

    @staticmethod
    def int(x):
        """
        Helper method to convert an RPython Signed into a C int
        """
        return rffi.cast(rffi.INT_real, x)

    @staticmethod
    def cast(typename, x):
        """
        Helper method to convert an RPython value into the correct C return
        type.
        """
        lltype = llapi.cts.gettype(typename)
        return rffi.cast(lltype, x)

    @staticmethod
    def ccharp2text(space, ptr):
        """
        Convert a C const char* into a W_UnicodeObject
        """
        s = rffi.constcharp2str(ptr)
        return space.newtext(s)



API = APISet(llapi.cts, is_debug=False)
DEBUG = APISet(llapi.cts, is_debug=True)
