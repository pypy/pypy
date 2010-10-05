from pypy.rpython.lltypesystem import lltype, rffi

def run_asm(asm):
    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)
    addr = asm.mc.baseaddr()#executable_token._arm_bootstrap_code
    assert addr % 8 == 0
    func = rffi.cast(lltype.Ptr(BOOTSTRAP_TP), addr)
    return func()

def skip_unless_arm(f):
    import os
    def skip_it(*args):
        import py
        py.test.skip('only for arm')

    func = skip_it
    try:
        if os.uname()[4].index('arm') >= 0:
            func=f
    finally:
        return func
