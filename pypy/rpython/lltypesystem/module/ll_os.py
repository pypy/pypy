import os
from pypy.rpython.module.support import to_rstr

def ll_os_getcwd():
    return to_rstr(os.getcwd())
ll_os_getcwd.suggested_primitive = True

