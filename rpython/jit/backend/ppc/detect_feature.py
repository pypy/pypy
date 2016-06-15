import sys
import struct
import platform
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform
from rpython.rlib.rmmap import alloc, free
from rpython.rlib.rstruct.runpack import runpack

AT_HWCAP = rffi_platform.getconstantinteger('AT_HWCAP', '#include "linux/auxvec.h"')
AT_NULL = rffi_platform.getconstantinteger('AT_NULL', '#include "linux/auxvec.h"')
PPC_FEATURE_HAS_ALTIVEC = rffi_platform.getconstantinteger('PPC_FEATURE_HAS_ALTIVEC',
                                                   '#include "asm/cputable.h"')
SYSTEM = platform.system()

def detect_vsx_linux():
    with open('/proc/self/auxv', 'rb') as fd:
        while True:
            buf = fd.read(16)
            if not buf:
                break
            key, value = runpack("LL", buf)
            if key == AT_HWCAP:
                if value & PPC_FEATURE_HAS_ALTIVEC:
                    return True
            if key == AT_NULL:
                return False
    return False

def detect_vsx():
    if SYSTEM == 'Linux':
        return detect_vsx_linux()
    return False

if __name__ == '__main__':
    print 'The following extensions are supported:'
    if detect_vsx():
        print '  - AltiVec'
