from rpython.translator.backendopt import graphanalyze
from rpython.translator.stm import funcgen


TRANSACTION_BREAK = set([
    'stm_commit_if_not_atomic',
    'stm_start_if_not_atomic',
    #'stm_partial_commit_and_resume_other_threads', # new priv_revision
    #'jit_assembler_call',
    'stm_enter_callback_call',
    'stm_leave_callback_call',
    'stm_transaction_break',
    ])

for tb in TRANSACTION_BREAK:
    assert hasattr(funcgen, tb)


class TransactionBreakAnalyzer(graphanalyze.BoolGraphAnalyzer):

    def analyze_simple_operation(self, op, graphinfo):
        return op.opname in TRANSACTION_BREAK

    def analyze_external_call(self, op, seen=None):
        # if 'funcobj' releases the GIL, then the GIL-releasing
        # functions themselves will call stm_commit_transaction
        # and stm_begin_inevitable_transaction.  This case is
        # covered above.
        return False
