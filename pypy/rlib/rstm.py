import threading
from pypy.translator.stm import stmgcintf
from pypy.rlib.debug import ll_assert
from pypy.rlib.objectmodel import keepalive_until_here, specialize
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import (cast_base_ptr_to_instance,
                                      cast_instance_to_base_ptr,
                                      llhelper)

def before_external_call():
    llop.stm_stop_transaction(lltype.Void)
    stmgcintf.StmOperations.commit_transaction()
before_external_call._dont_reach_me_in_del_ = True
before_external_call._transaction_break_ = True

def after_external_call():
    stmgcintf.StmOperations.begin_inevitable_transaction()
    llop.stm_start_transaction(lltype.Void)
after_external_call._dont_reach_me_in_del_ = True
after_external_call._transaction_break_ = True

def enter_callback_call():
    token = stmgcintf.StmOperations.descriptor_init()
    stmgcintf.StmOperations.begin_inevitable_transaction()
    if token != 1:
        llop.stm_start_transaction(lltype.Void)
    #else: the StmGCTLS is not built yet.  leave it to gc_thread_start()
    return token
enter_callback_call._dont_reach_me_in_del_ = True
enter_callback_call._transaction_break_ = True

def leave_callback_call(token):
    if token != 1:
        llop.stm_stop_transaction(lltype.Void)
    #else: the StmGCTLS is already destroyed, done by gc_thread_die()
    stmgcintf.StmOperations.commit_transaction()
    if token == 1:
        stmgcintf.StmOperations.descriptor_done()
leave_callback_call._dont_reach_me_in_del_ = True
leave_callback_call._transaction_break_ = True

# ____________________________________________________________

@specialize.memo()
def _get_stm_callback(func, argcls):
    def _stm_callback(llarg, retry_counter):
        llop.stm_start_transaction(lltype.Void)
        llarg = rffi.cast(rclass.OBJECTPTR, llarg)
        arg = cast_base_ptr_to_instance(argcls, llarg)
        try:
            func(arg, retry_counter)
        finally:
            llop.stm_stop_transaction(lltype.Void)
    return _stm_callback

@specialize.arg(0, 1)
def perform_transaction(func, argcls, arg):
    ll_assert(arg is None or isinstance(arg, argcls),
              "perform_transaction: wrong class")
    before_external_call()
    llarg = cast_instance_to_base_ptr(arg)
    llarg = rffi.cast(rffi.VOIDP, llarg)
    adr_of_top = llop.gc_adr_of_root_stack_top(llmemory.Address)
    #
    callback = _get_stm_callback(func, argcls)
    llcallback = llhelper(stmgcintf.StmOperations.CALLBACK_TX, callback)
    stmgcintf.StmOperations.perform_transaction(llcallback, llarg, adr_of_top)
    after_external_call()
    keepalive_until_here(arg)
