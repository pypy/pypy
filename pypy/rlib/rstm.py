from pypy.translator.stm import stmgcintf
from pypy.rlib.debug import ll_assert


def before_external_call():
    stmgcintf.StmOperations.commit_transaction()
before_external_call._gctransformer_hint_cannot_collect_ = True
before_external_call._dont_reach_me_in_del_ = True

def after_external_call():
    stmgcintf.StmOperations.begin_inevitable_transaction()
after_external_call._gctransformer_hint_cannot_collect_ = True
after_external_call._dont_reach_me_in_del_ = True

def enter_callback_call():
    new_thread = stmgcintf.StmOperations.descriptor_init()
    stmgcintf.StmOperations.begin_inevitable_transaction()
    return new_thread
enter_callback_call._gctransformer_hint_cannot_collect_ = True
enter_callback_call._dont_reach_me_in_del_ = True

def leave_callback_call(token):
    stmgcintf.StmOperations.commit_transaction()
    if token == 1:
        stmgcintf.StmOperations.descriptor_done()
leave_callback_call._gctransformer_hint_cannot_collect_ = True
leave_callback_call._dont_reach_me_in_del_ = True

def do_yield_thread():
    stmgcintf.StmOperations.do_yield_thread()
do_yield_thread._gctransformer_hint_close_stack_ = True
do_yield_thread._dont_reach_me_in_del_ = True
