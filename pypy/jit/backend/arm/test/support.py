from pypy.rpython.lltypesystem import lltype, rffi

def run_asm(asm):
    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)
    addr = asm.mc.baseaddr()#executable_token._arm_bootstrap_code
    assert addr % 8 == 0
    func = rffi.cast(lltype.Ptr(BOOTSTRAP_TP), addr)
    return func()

def skip_unless_arm():
    import os
    import py

    skip = True
    try:
        if os.uname()[4].index('arm') >= 0:
            skip = False
    finally:
        if skip:
            py.test.skip('only for arm')

