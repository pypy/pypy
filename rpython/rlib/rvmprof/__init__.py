from rpython.rlib.objectmodel import specialize
from rpython.rlib.rvmprof.rvmprof import _get_vmprof, VMProfError
from rpython.rlib.rvmprof.rvmprof import vmprof_execute_code, MAX_FUNC_NAME
from rpython.rlib.rvmprof.rvmprof import _was_registered
from rpython.rlib.rvmprof.cintf import VMProfPlatformUnsupported

#
# See README.txt.
#


#vmprof_execute_code(): implemented directly in rvmprof.py

def register_code_object_class(CodeClass, full_name_func):
    _get_vmprof().register_code_object_class(CodeClass, full_name_func)

@specialize.argtype(0)
def register_code(code, name):
    _get_vmprof().register_code(code, name)

@specialize.call_location()
def get_unique_id(code):
    """Return the internal unique ID of a code object.  Can only be
    called after register_code().  Call this in the jitdriver's
    method 'get_unique_id(*greenkey)'.  This always returns 0 if we
    didn't call register_code_object_class() on the class.
    """
    assert code is not None
    if _was_registered(code.__class__):
        # '0' can occur here too, if the code object was prebuilt,
        # or if register_code() was not called for another reason.
        return code._vmprof_unique_id
    return 0

def enable(fileno, interval, memory=0, native=0):
    _get_vmprof().enable(fileno, interval, memory, native)

def disable():
    _get_vmprof().disable()
