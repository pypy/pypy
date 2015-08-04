from rpython.rlib.objectmodel import specialize
from rpython.rlib.rvmprof.rvmprof import _get_vmprof, VMProfError
from rpython.rlib.rvmprof.rvmprof import vmprof_execute_code, MAX_FUNC_NAME

#
# See README.txt.
#


#vmprof_execute_code(): implemented directly in rvmprof.py

def register_code_object_class(CodeClass, full_name_func):
    _get_vmprof().register_code_object_class(CodeClass, full_name_func)

@specialize.argtype(1)
def register_code(code, name):
    _get_vmprof().register_code(code, name)

def enable(fileno, interval):
    _get_vmprof().enable(fileno, interval)

def disable():
    _get_vmprof().disable()
