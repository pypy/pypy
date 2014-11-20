import sys
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rmmap import alloc, free


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

def detect_x32_mode():
    data = alloc(4096)
    pos = 0                         # 32-bit         64-bit / x32
    for c in ("\x48"                # DEC EAX
              "\xB8\xC8\x00\x00\x00"# MOV EAX, 200   MOV RAX, 0x40404040000000C8
              "\x40\x40\x40\x40"    # 4x INC EAX
              "\xC3"):              # RET            RET
        data[pos] = c
        pos += 1
    fnptr = rffi.cast(lltype.Ptr(lltype.FuncType([], lltype.Signed)), data)
    code = fnptr()
    free(data, 4096)
    assert code in (200, 204, 0x40404040000000C8)
    return code == 200


if __name__ == '__main__':
    if detect_sse2():
        print 'Processor supports sse2.'
    else:
        print 'Missing processor support for sse2.'
    if detect_x32_mode():
        print 'Process is running in "x32" mode.'
