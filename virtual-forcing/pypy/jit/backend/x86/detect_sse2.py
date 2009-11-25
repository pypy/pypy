import autopath
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rmmap import alloc, free


def detect_sse2():
    data = alloc(4096)
    pos = 0
    for c in ("\xB8\x01\x00\x00\x00"     # MOV EAX, 1
              "\x53"                     # PUSH EBX
              "\x0F\xA2"                 # CPUID
              "\x5B"                     # POP EBX
              "\x92"                     # XCHG EAX, EDX
              "\xC3"):                   # RET
        data[pos] = c
        pos += 1
    fnptr = rffi.cast(lltype.Ptr(lltype.FuncType([], lltype.Signed)), data)
    code = fnptr()
    free(data, 4096)
    return bool(code & (1<<25)) and bool(code & (1<<26))


if __name__ == '__main__':
    if detect_sse2():
        print 'Processor supports sse2.'
    else:
        print 'Missing processor support for sse2.'
