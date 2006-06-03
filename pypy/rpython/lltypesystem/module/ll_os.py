import os
from pypy.rpython.module.support import from_rstr, to_rstr
from pypy.rpython.module.ll_os import *

def ll_os_open(fname, flag, mode):
    return os.open(from_rstr(fname), flag, mode)
ll_os_open.suggested_primitive = True

def ll_os_write(fd, astring):
    return os.write(fd, from_rstr(astring))
ll_os_write.suggested_primitive = True

def ll_os_getcwd():
    return to_rstr(os.getcwd())
ll_os_getcwd.suggested_primitive = True

