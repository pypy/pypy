from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform

class CConfig:
    _includes_ = ("sys/types.h", "sys/mman.h")
    size_t = platform.SimpleType("size_t", rffi.ULONG)
    off_t = platform.SimpleType("off_t", rffi.LONG)

    MAP_PRIVATE   = platform.ConstantInteger("MAP_PRIVATE")
    MAP_ANON      = platform.DefinedConstantInteger("MAP_ANON")
    MAP_ANONYMOUS = platform.DefinedConstantInteger("MAP_ANONYMOUS")
    PROT_READ     = platform.ConstantInteger("PROT_READ")
    PROT_WRITE    = platform.ConstantInteger("PROT_WRITE")
    PROT_EXEC     = platform.ConstantInteger("PROT_EXEC")

globals().update(platform.configure(CConfig))
if MAP_ANONYMOUS is None:
    MAP_ANONYMOUS = MAP_ANON
    assert MAP_ANONYMOUS is not None
del MAP_ANON

# ____________________________________________________________

PTR = rffi.CCHARP

mmap_ = rffi.llexternal('mmap',
                        [PTR, size_t, rffi.INT, rffi.INT, rffi.INT, off_t],
                        PTR,
                        includes = ["sys/mman.h"])
munmap_ = rffi.llexternal('munmap',
                          [PTR, size_t],
                          rffi.INT,
                          includes = ["sys/mman.h"])

class Hint:
    pos = -0x4fff0000   # for reproducible results
hint = Hint()

def alloc(map_size):
    flags = MAP_PRIVATE | MAP_ANONYMOUS
    prot = PROT_EXEC | PROT_READ | PROT_WRITE
    hintp = rffi.cast(PTR, hint.pos)
    res = mmap_(hintp, map_size, prot, flags, -1, 0)
    if res == rffi.cast(PTR, -1):
        raise MemoryError
    hint.pos += map_size
    return res

free = munmap_
