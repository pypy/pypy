import thread
from pypy.rlib.objectmodel import specialize, we_are_translated, keepalive_until_here
from pypy.rpython.lltypesystem import rffi, lltype, rclass
from pypy.rpython.annlowlevel import (cast_base_ptr_to_instance,
                                      cast_instance_to_base_ptr,
                                      llhelper)
from pypy.translator.stm import _rffi_stm

_global_lock = thread.allocate_lock()

@specialize.memo()
def _get_stm_callback(func, argcls):
    def _stm_callback(llarg, retry_counter):
        if we_are_translated():
            llarg = rffi.cast(rclass.OBJECTPTR, llarg)
            arg = cast_base_ptr_to_instance(argcls, llarg)
        else:
            arg = lltype.TLS.stm_callback_arg
        res = func(arg, retry_counter)
        assert res is None
        return lltype.nullptr(rffi.VOIDP.TO)
    return _stm_callback

@specialize.arg(0, 1)
def perform_transaction(func, argcls, arg):
    assert isinstance(arg, argcls)
    assert argcls._alloc_nonmovable_
    if we_are_translated():
        llarg = cast_instance_to_base_ptr(arg)
        llarg = rffi.cast(rffi.VOIDP, llarg)
    else:
        # only for tests: we want (1) to test the calls to the C library,
        # but also (2) to work with multiple Python threads, so we acquire
        # and release some custom GIL here --- even though it doesn't make
        # sense from an STM point of view :-/
        _global_lock.acquire()
        lltype.TLS.stm_callback_arg = arg
        llarg = lltype.nullptr(rffi.VOIDP.TO)
    callback = _get_stm_callback(func, argcls)
    llcallback = llhelper(_rffi_stm.CALLBACK, callback)
    _rffi_stm.stm_perform_transaction(llcallback, llarg)
    keepalive_until_here(arg)
    if not we_are_translated():
        _global_lock.release()

def descriptor_init():
    if not we_are_translated(): _global_lock.acquire()
    _rffi_stm.stm_descriptor_init()
    if not we_are_translated(): _global_lock.release()

def descriptor_done():
    if not we_are_translated(): _global_lock.acquire()
    _rffi_stm.stm_descriptor_done()
    if not we_are_translated(): _global_lock.release()

def debug_get_state():
    return _rffi_stm.stm_debug_get_state()
