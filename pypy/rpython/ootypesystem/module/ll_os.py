import os
from pypy.rpython.ootypesystem.ootype import oostring

def ll_os_getcwd():
    return oostring(os.getcwd(), -1)
ll_os_getcwd.suggested_primitive = True

