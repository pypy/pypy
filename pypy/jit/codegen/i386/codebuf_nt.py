import ctypes
import pypy.rpython.rctypes.implementation
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.ctypes_platform import ConstantInteger
from pypy.rpython.rctypes.tool.ctypes_platform import SimpleType


raise NotImplementedError("this needs to be ported from rctypes to rffi")


class CConfig:
    _header_ = '#include <Windows.h>'

    SIZE_T                 = SimpleType('SIZE_T', ctypes.c_long)
    DWORD                  = SimpleType('DWORD', ctypes.c_long)
    BOOL                   = SimpleType('BOOL', ctypes.c_int)
    MEM_COMMIT             = ConstantInteger('MEM_COMMIT')
    MEM_RESERVE            = ConstantInteger('MEM_RESERVE')
    MEM_RELEASE            = ConstantInteger('MEM_RELEASE')
    PAGE_EXECUTE_READWRITE = ConstantInteger('PAGE_EXECUTE_READWRITE')

globals().update(ctypes_platform.configure(CConfig))

# cannot use c_void_p as return value of functions :-(
PTR = ctypes.POINTER(ctypes.c_char)

VirtualAlloc = ctypes.windll.kernel32.VirtualAlloc
VirtualAlloc.argtypes = [PTR, SIZE_T, DWORD, DWORD]
VirtualAlloc.restype = PTR

VirtualProtect = ctypes.windll.kernel32.VirtualProtect
VirtualProtect.argtypes = [PTR, SIZE_T, DWORD, ctypes.POINTER(DWORD)]
VirtualProtect.restype = BOOL

VirtualFree = ctypes.windll.kernel32.VirtualFree
VirtualFree.argtypes = [PTR, SIZE_T, DWORD]
VirtualFree.restype = BOOL

# ____________________________________________________________

def alloc(map_size):
    res = VirtualAlloc(PTR(), map_size, MEM_COMMIT|MEM_RESERVE,
                       PAGE_EXECUTE_READWRITE)
    if not res:
        raise MemoryError
    old = DWORD()
    VirtualProtect(res, map_size, PAGE_EXECUTE_READWRITE, ctypes.byref(old))
    # ignore errors, just try
    return res

def free(ptr, map_size):
    VirtualFree(ptr, 0, MEM_RELEASE)
