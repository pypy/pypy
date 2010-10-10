import os
import py

from pypy.rpython.lltypesystem import lltype, rffi

if os.uname()[1] == 'llaima.local':
    AS = '~/Code/arm-jit/android/android-ndk-r4b//build/prebuilt/darwin-x86/arm-eabi-4.4.0/arm-eabi/bin/as'
else:
    AS = 'as'

def run_asm(asm):
    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)
    addr = asm.mc.baseaddr()
    assert addr % 8 == 0
    func = rffi.cast(lltype.Ptr(BOOTSTRAP_TP), addr)
    return func()

def skip_unless_arm():
    check_skip(os.uname()[4])

def requires_arm_as():
    import commands
    i = commands.getoutput("%s -version </dev/null -o /dev/null 2>&1" % AS)
    check_skip(i)

def check_skip(inp, search='arm', msg='only for arm'):
    skip = True
    try:
        if inp.index(search) >= 0:
            skip = False
    finally:
        if skip:
            py.test.skip(msg)
