from pypy.translator.stm._rffi_stm import *
from pypy.rpython.annlowlevel import llhelper

def test_descriptor():
    stm_descriptor_init()
    stm_descriptor_done()

def test_stm_perform_transaction():
    def callback1(x, retry_counter):
        return lltype.nullptr(rffi.VOIDP.TO)
    stm_descriptor_init()
    stm_perform_transaction(llhelper(CALLBACK, callback1),
                        lltype.nullptr(rffi.VOIDP.TO))
    stm_descriptor_done()

def test_stm_abort_and_retry():
    A = lltype.Struct('A', ('x', lltype.Signed), ('y', lltype.Signed))
    a = lltype.malloc(A, immortal=True, flavor='raw')
    a.y = 0
    def callback1(x, retry_counter):
        assert retry_counter == a.y
        if a.y < 10:
            a.y += 1    # non-transactionally
            stm_abort_and_retry()
        else:
            a.x = 42 * a.y
            return lltype.nullptr(rffi.VOIDP.TO)
    stm_descriptor_init()
    stm_perform_transaction(llhelper(CALLBACK, callback1),
                        lltype.nullptr(rffi.VOIDP.TO))
    stm_descriptor_done()
    assert a.x == 420

def test_stm_abort_and_retry_transactionally():
    A = lltype.Struct('A', ('x', lltype.Signed), ('y', lltype.Signed))
    a = lltype.malloc(A, immortal=True, flavor='raw')
    a.x = -611
    a.y = 0
    def callback1(x, retry_counter):
        assert retry_counter == a.y
        assert a.x == -611
        p = lltype.direct_fieldptr(a, 'x')
        p = rffi.cast(SignedP, p)
        assert rffi.cast(lltype.Signed, stm_read_word(p)) == -611
        stm_write_word(p, 42 * a.y)
        assert rffi.cast(lltype.Signed, stm_read_word(p)) == 42 * a.y
        assert a.x == -611 # xxx still the old value when reading non-transact.
        if a.y < 10:
            a.y += 1    # non-transactionally
            stm_abort_and_retry()
        else:
            return lltype.nullptr(rffi.VOIDP.TO)
    stm_descriptor_init()
    stm_perform_transaction(llhelper(CALLBACK, callback1),
                            lltype.nullptr(rffi.VOIDP.TO))
    stm_descriptor_done()
    assert a.x == 420

def test_stm_debug_get_state():
    def callback1(x, retry_counter):
        assert stm_debug_get_state() == 1
        stm_try_inevitable()
        assert stm_debug_get_state() == 2
        return lltype.nullptr(rffi.VOIDP.TO)
    assert stm_debug_get_state() == -1
    stm_descriptor_init()
    assert stm_debug_get_state() == 0
    stm_perform_transaction(llhelper(CALLBACK, callback1),
                            lltype.nullptr(rffi.VOIDP.TO))
    stm_descriptor_done()
