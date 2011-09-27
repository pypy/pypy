from pypy.translator.stm._rffi_stm import *
from pypy.rpython.annlowlevel import llhelper

def test_descriptor():
    descriptor_init()
    descriptor_done()

def test_perform_transaction():
    def callback1(x):
        return lltype.nullptr(rffi.VOIDP.TO)
    descriptor_init()
    perform_transaction(llhelper(CALLBACK, callback1),
                        lltype.nullptr(rffi.VOIDP.TO))
    descriptor_done()

def test_abort_and_retry():
    A = lltype.Struct('A', ('x', lltype.Signed), ('y', lltype.Signed))
    a = lltype.malloc(A, immortal=True, flavor='raw')
    a.y = 0
    def callback1(x):
        if a.y < 10:
            a.y += 1    # non-transactionally
            abort_and_retry()
        else:
            a.x = 42 * a.y
            return lltype.nullptr(rffi.VOIDP.TO)
    descriptor_init()
    perform_transaction(llhelper(CALLBACK, callback1),
                        lltype.nullptr(rffi.VOIDP.TO))
    descriptor_done()
    assert a.x == 420
