from pypy.translator.stm import stmgcintf


def before_external_call():
    stmgcintf.StmOperations.before_external_call()
before_external_call._gctransformer_hint_cannot_collect_ = True
before_external_call._dont_reach_me_in_del_ = True

def after_external_call():
    stmgcintf.StmOperations.after_external_call()
after_external_call._gctransformer_hint_cannot_collect_ = True
after_external_call._dont_reach_me_in_del_ = True

def do_yield_thread():
    stmgcintf.StmOperations.do_yield_thread()
do_yield_thread._gctransformer_hint_close_stack_ = True
do_yield_thread._dont_reach_me_in_del_ = True
