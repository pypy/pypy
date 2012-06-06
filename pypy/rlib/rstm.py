import threading
from pypy.translator.stm import stmgcintf
from pypy.rlib.debug import ll_assert, fatalerror
from pypy.rlib.objectmodel import keepalive_until_here, specialize
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rposix import get_errno, set_errno
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import (cast_base_ptr_to_instance,
                                      cast_instance_to_base_ptr,
                                      llhelper)

def is_inevitable():
    return we_are_translated() and stmgcintf.StmOperations.is_inevitable()

def should_break_transaction():
    return we_are_translated() and (
        stmgcintf.StmOperations.should_break_transaction())

def set_transaction_length(length):
    stmgcintf.StmOperations.set_transaction_length(length)

def increment_atomic():
    stmgcintf.StmOperations.add_atomic(+1)

def decrement_atomic():
    stmgcintf.StmOperations.add_atomic(-1)

def is_atomic():
    return stmgcintf.StmOperations.get_atomic()

def before_external_call():
    if not is_atomic():
        e = get_errno()
        llop.stm_stop_transaction(lltype.Void)
        stmgcintf.StmOperations.commit_transaction()
        set_errno(e)
before_external_call._dont_reach_me_in_del_ = True
before_external_call._transaction_break_ = True

def after_external_call():
    if not is_atomic():
        e = get_errno()
        stmgcintf.StmOperations.begin_inevitable_transaction()
        llop.stm_start_transaction(lltype.Void)
        set_errno(e)
after_external_call._dont_reach_me_in_del_ = True
after_external_call._transaction_break_ = True

def enter_callback_call():
    token = stmgcintf.StmOperations.descriptor_init()
    if token != 1:
        after_external_call()
    else:
        ll_assert(not is_atomic(), "new thread: is_atomic() != 0")
        stmgcintf.StmOperations.begin_inevitable_transaction()
        # the StmGCTLS is not built yet.  leave it to gc_thread_start()
    return token
enter_callback_call._dont_reach_me_in_del_ = True
enter_callback_call._transaction_break_ = True

def leave_callback_call(token):
    if token != 1:
        before_external_call()
    else:
        # the StmGCTLS is already destroyed, done by gc_thread_die()
        # (we don't care if is_atomic() or not, we'll commit now)
        stmgcintf.StmOperations.commit_transaction()
        stmgcintf.StmOperations.descriptor_done()
leave_callback_call._dont_reach_me_in_del_ = True
leave_callback_call._transaction_break_ = True

# ____________________________________________________________

@specialize.memo()
def _get_stm_callback(func, argcls):
    def _stm_callback(llarg, retry_counter):
        if not is_atomic():
            llop.stm_start_transaction(lltype.Void)
        llarg = rffi.cast(rclass.OBJECTPTR, llarg)
        arg = cast_base_ptr_to_instance(argcls, llarg)
        try:
            res = func(arg, retry_counter)
        except:
            fatalerror("no exception allowed in stm_callback")
            assert 0
        if not is_atomic():
            llop.stm_stop_transaction(lltype.Void)
        return res
    return _stm_callback

@specialize.arg(0, 1)
def perform_transaction(func, argcls, arg):
    ll_assert(arg is None or isinstance(arg, argcls),
              "perform_transaction: wrong class")
    before_external_call()
    # Passing around the GC object 'arg' is a bit delicate.  At this point
    # it has been saved as a global, but 'arg' likely points to the object
    # with an offset 2, which is the flag used for "used to be a local".
    # We have to revert this flag here...
    llarg = cast_instance_to_base_ptr(arg)
    llarg = rffi.cast(lltype.Signed, llarg)
    llarg &= ~2
    llarg = rffi.cast(rffi.VOIDP, llarg)
    #
    adr_of_top = llop.gc_adr_of_root_stack_top(llmemory.Address)
    callback = _get_stm_callback(func, argcls)
    llcallback = llhelper(stmgcintf.StmOperations.CALLBACK_TX, callback)
    stmgcintf.StmOperations.perform_transaction(llcallback, llarg, adr_of_top)
    after_external_call()
    keepalive_until_here(arg)
perform_transaction._transaction_break_ = True
