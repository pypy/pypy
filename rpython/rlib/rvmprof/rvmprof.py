import sys, os
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.rstring import StringBuilder
from rpython.rlib import jit, rgc, rposix
from rpython.rlib.rvmprof import cintf
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
from rpython.rtyper.lltypesystem import rffi

MAX_CODES = 8000 - 255
MAX_FUNC_NAME = 255

# ____________________________________________________________


class VMProfError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class VMProf(object):

    def __init__(self):
        "NOT_RPYTHON: use get_vmprof()"
        self._code_classes = set()
        self._gather_all_code_objs = lambda: None
        self._cleanup_()
        if sys.maxint == 2147483647:
            self._code_unique_id = 0 # XXX this is wrong, it won't work on 32bit
        else:
            self._code_unique_id = 0x7000000000000000

    def _cleanup_(self):
        self.is_enabled = False
        self.fileno = -1
        self._current_codes = None

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
        if not (1e-6 <= interval < 1.0):
            raise VMProfError("bad value for 'interval'")
        interval_usec = int(interval * 1000000.0)

        p_error = cintf.vmprof_init(fileno)
        if p_error:
            raise VMProfError(rffi.charp2str(p_error))

        self.fileno = fileno
        self._write_header(interval_usec)
        self._gather_all_code_objs()
        res = cintf.vmprof_enable(interval_usec)
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
        if self._current_codes is not None:
            self._flush_codes()
        self.fileno = -1
        res = cintf.vmprof_disable()
        if res < 0:
            raise VMProfError(os.strerror(rposix.get_saved_errno()))

    def _write_code_registration(self, uid, name):
        assert name.count(':') == 3 and len(name) <= MAX_FUNC_NAME, (
            "the name must be 'class:func_name:func_line:filename' "
            "and at most %d characters; got '%s'" % (MAX_FUNC_NAME, name))
        b = self._current_codes
        if b is None:
            b = self._current_codes = StringBuilder()
        b.append('\x02')
        _write_long_to_string_builder(uid, b)
        _write_long_to_string_builder(len(name), b)
        b.append(name)
        if b.getlength() >= MAX_CODES:
            self._flush_codes()

    def _flush_codes(self):
        buf = self._current_codes.build()
        self._current_codes = None
        cintf.vmprof_write_buf(buf, len(buf))
        # NOTE: keep in mind that vmprof_write_buf() can only write
        # a maximum of 8184 bytes.  This should be guaranteed here because:
        assert MAX_CODES + 17 + MAX_FUNC_NAME <= 8184

    def _write_header(self, interval_usec):
        b = StringBuilder()
        _write_long_to_string_builder(0, b)
        _write_long_to_string_builder(3, b)
        _write_long_to_string_builder(0, b)
        _write_long_to_string_builder(interval_usec, b)
        _write_long_to_string_builder(0, b)
        b.append('\x04') # interp name
        b.append(chr(len('pypy')))
        b.append('pypy')
        buf = b.build()
        cintf.vmprof_write_buf(buf, len(buf))


def _write_long_to_string_builder(l, b):
    b.append(chr(l & 0xff))
    b.append(chr((l >> 8) & 0xff))
    b.append(chr((l >> 16) & 0xff))
    b.append(chr((l >> 24) & 0xff))
    if sys.maxint > 2147483647:
        b.append(chr((l >> 32) & 0xff))
        b.append(chr((l >> 40) & 0xff))
        b.append(chr((l >> 48) & 0xff))
        b.append(chr((l >> 56) & 0xff))


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
