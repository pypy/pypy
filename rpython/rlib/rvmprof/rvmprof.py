import sys, os
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib import jit, rgc, rposix
from rpython.rlib.rvmprof import cintf
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
from rpython.rtyper.lltypesystem import rffi

MAX_FUNC_NAME = 1023

# ____________________________________________________________


class VMProfError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class VMProf(object):

    def __init__(self):
        "NOT_RPYTHON: use _get_vmprof()"
        self._code_classes = set()
        self._gather_all_code_objs = lambda: None
        self._cleanup_()
        if sys.maxint == 2147483647:
            self._code_unique_id = 0 # XXX this is wrong, it won't work on 32bit
        else:
            self._code_unique_id = 0x7000000000000000
        self.cintf = cintf.setup()

    def _cleanup_(self):
        self.is_enabled = False

    @specialize.argtype(1)
    def register_code(self, code, full_name_func):
        """Register the code object.  Call when a new code object is made.
        """
        if code._vmprof_unique_id == 0:
            # Add 4 to the next unique_id, so that all returned numbers are
            # multiples of 4.  This is also a workaround for a bug (in some
            # revision) of vmprof-python, where it will look up the name
            # corresponding the 'uid + 1' instead of 'uid': if the next one
            # is at 'uid + 4', then the lookup will give the right answer
            # anyway.
            uid = self._code_unique_id + 4
            code._vmprof_unique_id = uid
            self._code_unique_id = uid
            if self.is_enabled:
                self._write_code_registration(uid, full_name_func(code))

    def register_code_object_class(self, CodeClass, full_name_func):
        """NOT_RPYTHON
        Register statically the class 'CodeClass' as containing user
        code objects.

        full_name_func() is a function called at runtime with an
        instance of CodeClass and it should return a string.  This
        is the string stored in the vmprof file identifying the code
        object.  It can be directly an unbound method of CodeClass.
        IMPORTANT: the name returned must be at most MAX_FUNC_NAME
        characters long, and with exactly 3 colons, i.e. of the form

            class:func_name:func_line:filename

        where 'class' is 'py' for PyPy.

        Instances of the CodeClass will have a new attribute called
        '_vmprof_unique_id', but that's managed internally.
        """
        if CodeClass in self._code_classes:
            return
        CodeClass._vmprof_unique_id = 0     # default value: "unknown"
        self._code_classes.add(CodeClass)
        #
        def try_cast_to_code(gcref):
            return rgc.try_cast_gcref_to_instance(CodeClass, gcref)
        #
        def gather_all_code_objs():
            all_code_objs = rgc.do_get_objects(try_cast_to_code)
            for code in all_code_objs:
                uid = code._vmprof_unique_id
                if uid != 0:
                    self._write_code_registration(uid, full_name_func(code))
            prev()
        # make a chained list of the gather() functions for all
        # the types of code objects
        prev = self._gather_all_code_objs
        self._gather_all_code_objs = gather_all_code_objs

    def enable(self, fileno, interval):
        """Enable vmprof.  Writes go to the given 'fileno'.
        The sampling interval is given by 'interval' as a number of
        seconds, as a float which must be smaller than 1.0.
        Raises VMProfError if something goes wrong.
        """
        assert fileno >= 0
        if self.is_enabled:
            raise VMProfError("vmprof is already enabled")

        p_error = self.cintf.vmprof_init(fileno, interval, "pypy")
        if p_error:
            raise VMProfError(rffi.charp2str(p_error))

        self._gather_all_code_objs()
        res = self.cintf.vmprof_enable()
        if res < 0:
            raise VMProfError(os.strerror(rposix.get_saved_errno()))
        self.is_enabled = True

    def disable(self):
        """Disable vmprof.
        Raises VMProfError if something goes wrong.
        """
        if not self.is_enabled:
            raise VMProfError("vmprof is not enabled")
        self.is_enabled = False
        res = self.cintf.vmprof_disable()
        if res < 0:
            raise VMProfError(os.strerror(rposix.get_saved_errno()))

    def _write_code_registration(self, uid, name):
        assert name.count(':') == 3 and len(name) <= MAX_FUNC_NAME, (
            "the name must be 'class:func_name:func_line:filename' "
            "and at most %d characters; got '%s'" % (MAX_FUNC_NAME, name))
        if self.cintf.vmprof_register_virtual_function(name, uid, 500000) < 0:
            raise VMProfError("vmprof buffers full!  disk full or too slow")


def vmprof_execute_code(name, get_code_fn, result_class=None):
    """Decorator to be used on the function that interprets a code object.

    'name' must be a unique name.

    'get_code_fn(*args)' is called to extract the code object from the
    arguments given to the decorated function.

    The original function can return None, an integer, or an instance.
    In the latter case (only), 'result_class' must be set.

    NOTE: for now, this assumes that the decorated functions only takes
    instances or plain integer arguments, and at most 5 of them
    (including 'self' if applicable).
    """
    def decorate(func):
        try:
            _get_vmprof()
        except cintf.VMProfPlatformUnsupported:
            return func

        if hasattr(func, 'im_self'):
            assert func.im_self is None
            func = func.im_func

        def lower(*args):
            if len(args) == 0:
                return (), ""
            ll_args, token = lower(*args[1:])
            ll_arg = args[0]
            if isinstance(ll_arg, int):
                tok = "i"
            else:
                tok = "r"
                ll_arg = cast_instance_to_gcref(ll_arg)
            return (ll_arg,) + ll_args, tok + token

        @specialize.memo()
        def get_ll_trampoline(token):
            if result_class is None:
                restok = "i"
            else:
                restok = "r"
            return cintf.make_trampoline_function(name, func, token, restok)

        def decorated_function(*args):
            # go through the asm trampoline ONLY if we are translated but not
            # being JITted.
            #
            # If we are not translated, we obviously don't want to go through
            # the trampoline because there is no C function it can call.
            #
            # If we are being JITted, we want to skip the trampoline, else the
            # JIT cannot see through it.
            #
            if we_are_translated() and not jit.we_are_jitted():
                # if we are translated, call the trampoline
                unique_id = get_code_fn(*args)._vmprof_unique_id
                ll_args, token = lower(*args)
                ll_trampoline = get_ll_trampoline(token)
                ll_result = ll_trampoline(*ll_args + (unique_id,))
                if result_class is not None:
                    return cast_base_ptr_to_instance(result_class, ll_result)
                else:
                    return ll_result
            else:
                return func(*args)
        decorated_function.__name__ = func.__name__ + '_rvmprof'
        return decorated_function

    return decorate

@specialize.memo()
def _was_registered(CodeClass):
    return hasattr(CodeClass, '_vmprof_unique_id')


_vmprof_instance = None

@specialize.memo()
def _get_vmprof():
    global _vmprof_instance
    if _vmprof_instance is None:
        _vmprof_instance = VMProf()
    return _vmprof_instance
