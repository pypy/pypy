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
