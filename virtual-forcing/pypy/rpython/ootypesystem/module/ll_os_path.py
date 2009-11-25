from pypy.rpython.module.support import OOSupport
from pypy.rpython.module.ll_os_path import BaseOsPath

class Implementation(BaseOsPath, OOSupport):
    pass
