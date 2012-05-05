from pypy.translator.stm import stmgcintf
from pypy.rlib.debug import ll_assert
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop


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

def do_yield_thread():
    stmgcintf.StmOperations.do_yield_thread()
do_yield_thread._gctransformer_hint_close_stack_ = True
do_yield_thread._dont_reach_me_in_del_ = True
do_yield_thread._transaction_break_ = True
