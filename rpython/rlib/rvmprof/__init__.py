from rpython.rlib.objectmodel import specialize
from rpython.rlib.rvmprof.rvmprof import _get_vmprof, VMProfError
from rpython.rlib.rvmprof.rvmprof import vmprof_execute_code, MAX_FUNC_NAME
from rpython.rlib.rvmprof.rvmprof import _was_registered

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
    assert code is not None
    if _was_registered(code.__class__):
        return _get_vmprof().get_unique_id(code)
    return 0

def enable(fileno, interval):
    _get_vmprof().enable(fileno, interval)

def disable():
    _get_vmprof().disable()
