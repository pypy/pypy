from rpython.rtyper.lltypesystem import lltype, rffi

def run_asm(asm):
    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)
    addr = asm.mc.materialize(asm.cpu, [], None)
    assert addr % 8 == 0
    func = rffi.cast(lltype.Ptr(BOOTSTRAP_TP), addr)
    asm.mc._dump_trace(addr, 'test.asm')
    return func()
